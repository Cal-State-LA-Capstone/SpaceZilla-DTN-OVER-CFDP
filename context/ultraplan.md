Context
The repo currently has a mismatch: controller.py runs a FastAPI/uvicorn IPC server on the host, and backend/docker_backend.py starts an ION container — but the pyion call-site (backend/pyion_adapter.py, used by backend/transfer_backend.py) runs on the host, not in the container. pyion needs the ION daemon in its own process tree, so host-side pyion can't talk to containerised ION. CFDP transfers therefore never actually work end-to-end in the current docker_main layout.
On top of that, the active main window is still the older frontend/SpaceZilla_ver0/ (wired via frontend/__init__.py::show_main_window), while the usable GUI (contact list, theming, dialogs, file-filter tree) lives in frontend/SpaceZilla_ver1/.
The goal is to:

Move the pyion/backend code into the container and expose it to the host through a small IPC channel.
Replace FastAPI+uvicorn+httpx with pyzmq REQ/REP (commands) plus a PUB socket (async CFDP events).
Swap the host's main-window loader to SpaceZilla_ver1.
Give the container read-only access to the host filesystem via a non-copying bind mount (opt-in, one consent prompt per machine) so pyion can cfdp_send host files in-place without any pre-transfer copy.
Keep the old code in place — add new modules alongside, add DEPRECATED headers to the old entry points, don't delete.
Add unit tests around container health, port exposure, host-mount accessibility, and end-to-end CFDP send.

CFDP/ION/PyION grounding (from NASA docs + existing code): pyion API = pyion.get_bp_proxy(node_num) → .bp_open(eid) and pyion.get_cfdp_proxy(node_num) → .cfdp_open(peer_entity, endpoint); the returned entity exposes cfdp_send, cfdp_request, register_event_handler, wait_for_transaction_end, cfdp_report. cfdp_send(source_file, dest_file, mode) reads source_file straight from disk at send time — the bind mount means host paths remapped to /host/... read the same bytes without any copy. The ionstart.rc format is the ionadmin / bpadmin / ipnadmin / cfdpadmin section list already shown in docker/nodes/configs/node1.rc. Two containers can reach each other by Docker DNS (node2:4556) on a shared bridge network. These match what backend/pyion_adapter.py and backend/rc_generator.py already encode — so no rewrite of the adapter is needed, only relocation.
Architecture (before vs after)
BEFORE  (host pyion can't see container ION — dead path)
 ┌──────────┐  http   ┌───────────────────────┐   docker run   ┌─────────────────┐
 │ GUI ver0 │────────▶│ Controller (FastAPI)  │───────────────▶│ container: ION  │
 └──────────┘         │  host-side pyion ✗    │                └─────────────────┘
                      └───────────────────────┘

AFTER
 ┌──────────┐ QtSignals ┌─────────────────────┐  ZMQ REQ :Nrep  ┌──────────────────────────────┐
 │ GUI ver1 │──────────▶│ ZmqController (host)│────────────────▶│ container: ION + pyion agent │
 └──────────┘           │   + IpcClient       │◀───────────────│    backend.container_agent   │
      ▲                 └─────────────────────┘  ZMQ PUB :Npub  │    pyion adapter (in-proc)   │
      │                       ▲                                 └──────────────────────────────┘
      └──── Qt signal ────────┘   (SubscriberThread → Qt signal)
One container per SpaceZilla process (per user's answer). Two dynamic host ports per container: rep_port (commands) and pub_port (events). Bind on 127.0.0.1 only. The host root is bind-mounted read-only at /host inside the container (see "Host filesystem access" below).
Host filesystem access (non-copying bind mount)
Goal: when the user picks /home/alice/photo.jpg in the GUI, the exact same bytes on the host disk are read by the container at send time — no pre-copy into the container, no staging dir.

Mount shape (backend/docker_backend.py::start_container): add -v /:/host:ro,rslave on Linux/macOS. ro protects the host from a compromised container. rslave propagates new sub-mounts (e.g. plugged-in drives) into the container without re-running. On Windows, fall back to -v //./:/host:ro and log a warning if it fails — Windows Docker Desktop doesn't always allow a full-drive mount, so the user may have to pick files from mounted subdirs only.
Consent gate: add store.globals field host_mount_consent: bool = False and host_mount_consent_at: str|None = None. On first boot, if host_mount_consent is False, frontend/main_window_ver1.show_main_window (before calling client.connect) shows a modal QMessageBox.question titled "Allow container to read your files?" with body text explaining: the mount is read-only, covers the entire host /, is needed so CFDP can send files without copying, and can be revoked later from Settings. On "Yes", write host_mount_consent=True via store.save_settings(...). On "No", set a flag on the window so file_send shows a QMessageBox explaining transfers are disabled until consent is granted. Until consent is granted, ZmqController.boot() starts the container without -v /:/host:ro — so refusing consent is safe and leaves the container isolated.
Path translation (host → container): add backend/ipc/path_map.py::to_container_path(host_path: str) -> str that prepends /host (with POSIX normalisation; on Windows translate C:\x\y → /host/c/x/y). frontend/main_window_ver1.py calls to_container_path on every path before client.queue_files([...]). The container side stores both — the queue dict carries path (container-visible) and display_name (basename for the UI).
Revoke: add a "Revoke host access" item under the Settings menu in SpaceZilla_ver1 (wire it into spaceZillaMainThemeAndDialogs.py::settingsMenu). Sets host_mount_consent=False and shows a dialog that the change takes effect next boot.
Safety notes:

Mount is always ro — the container cannot modify host files. Received files still land in the in-container /SZ_received_files directory (no host write path for now).
The consent prompt is shown once per machine, keyed in global settings, not per node.
The container does not run as root on the host — user is already in the docker group (per README_docker.md). UID mismatches are fine for ro reads.



Files to ADD

backend/ipc/__init__.py
backend/ipc/protocol.py — shared constants & JSON schema. Request: {"id": str, "method": str, "args": dict}. Reply: {"id": str, "ok": bool, "result": Any, "error": str|None}. Event (PUB): {"topic": "cfdp", "queue_id": str, "status": str}. Method list: health, startup_check, connect, disconnect, is_connected, queue_files, remove_file, clear_queue, get_queue, send_files, status_indicator.
backend/ipc/server.py — serve(rep_port, pub_port, facade) binds tcp://*:{rep_port} (REP) and tcp://*:{pub_port} (PUB). Dispatcher looks up method in a whitelist bound to BackendFacade. On send_files, it passes an on_change that publishes a PUB event.
backend/ipc/client.py — IpcClient(rep_port, pub_port, host="127.0.0.1"). Methods mirror BackendFacade. Uses zmq.Context.instance(), a REQ socket with RCVTIMEO=5000, retry once on timeout. subscribe(callback) starts a daemon thread on the PUB socket; callback runs on a worker thread — GUI code must marshal to Qt via QMetaObject.invokeMethod(..., Qt.QueuedConnection).
backend/container_agent.py — entrypoint run inside the container: python3 -m backend.container_agent --rep-port 5555 --pub-port 5556. Builds BackendFacade() and calls ipc.server.serve(...). Catches SIGTERM so docker stop unwinds cleanly.
backend/zmq_controller.py — host-side ZmqController (replaces controller.py's role). Boot sequence: store.load_config(node_id) → backend.build_image() → store.load_settings().host_mount_consent read → backend.start_container(config, host_mount=bool(consent)) (returns RunningContainer with mapped ports) → IpcClient(rep_port, pub_port) → client.health() loop until ready (1 s poll, 20 s budget) → store.save_state(..., status="running", ipc_port=rep_port, container_id=cid) → return True. Shutdown reverses: client.close() → backend.stop_container(cid) → store.save_state(status="stopped").
frontend/main_window_ver1.py — thin host-side glue. Imports frontend.SpaceZilla_ver1.spaceZillaMainThemeAndDialogs.MainWindow (the fuller version with dialogs), injects an IpcClient, before the first send checks store.load_settings().host_mount_consent and shows the consent QMessageBox.question if unset (writes result back via store.save_settings), translates host paths with backend.ipc.path_map.to_container_path, wires file_send.clicked → client.queue_files([container_path]) + client.send_files(), subscribes to PUB events, on each event finds the queue row by queue_id and updates its status label via a queued Qt signal. Also adds a "Revoke host access" action to the existing SETTINGS menu.
backend/ipc/path_map.py — to_container_path(host_path) (POSIX: /a/b → /host/a/b; Windows: C:\a\b → /host/c/a/b) plus the inverse to_host_path for display/logging. Pure functions, fully unit-testable without Docker.
tests/test_docker_backend_integration.py — @pytest.mark.integration (skip-if-no-docker fixture). test_container_running_after_boot, test_ports_exposed (asserts docker port <id> 5555/tcp and 5556/tcp both return 127.0.0.1:<nonzero>), test_stop_removes_container.
tests/test_ipc_roundtrip.py — integration. Boots container, asserts IpcClient.health() == {"ok": True}, asserts unknown method returns ok=False with "unknown_method" error.
tests/test_transfer_e2e.py — integration. Boots two nodes (node_num=1, node_num=2) with host_mount=True on a shared user-defined bridge network (docker network create spacezilla-test), each with its own generated rc that adds a TCP CLA pointing at the peer container name. Writes /tmp/hello.txt on the host, calls client1.queue_files(["/host/tmp/hello.txt"]) (via to_container_path), polls get_queue until status=="Completed" (30 s timeout), asserts file content matches via docker exec node2 cat /SZ_received_files/hello.txt. Verifies the bind mount is in-place: change the host file between two sends and assert the second send carries the new bytes without re-queuing from a different path.
tests/test_path_map.py — pure unit tests for backend/ipc/path_map.py (POSIX and Windows cases, idempotence, round-trip).
tests/test_host_mount.py — integration. Boots a container with host_mount=True, docker exec reads a file via /host/tmp/xxx and asserts content matches; boots another with host_mount=False and asserts /host does not exist inside the container.
conftest.py additions (or tests/conftest.py): docker_available fixture that pytest.skips if subprocess.run(["docker","info"]).returncode != 0; tmp_data_dir already exists — reuse.

Files to MODIFY (alongside old code, old files not deleted)

backend/docker_backend.py

start_container(config, *, host_mount: bool = False) → RunningContainer where RunningContainer = dataclass(container_id: str, rep_port: int, pub_port: int, host_mount: bool). Add -p 127.0.0.1:0:5555 -p 127.0.0.1:0:5556 so the OS assigns host ports; after docker run, parse them with docker port <id> 5555/tcp and 5556/tcp.
When host_mount=True, add -v /:/host:ro,rslave (Linux/macOS) or a platform-appropriate equivalent on Windows. Log the mount decision at INFO so it's visible in spacezilla.log.
Change CMD to bash -c "ionstart -I /home/ionstart.rc && python3 -m backend.container_agent --rep-port 5555 --pub-port 5556".
Add -v <repo>/backend:/opt/spacezilla/backend:ro and -e PYTHONPATH=/opt/spacezilla for dev, or bake the code into the image (see Dockerfile change). Default to baked.
Callers updated: the only caller is controller.py (deprecated) and the new zmq_controller.py. Keep old signature reachable via a tiny shim start_container_legacy that returns just the id — not used by new path; lets old controller.py still import without breakage.


docker/pyion_v414a2.dockerfile

After the existing pyion install steps, add:

RUN pip3 install --no-cache-dir pyzmq
COPY backend /opt/spacezilla/backend
COPY runtime_logger /opt/spacezilla/runtime_logger
ENV PYTHONPATH=/opt/spacezilla
EXPOSE 5555 5556


Default CMD stays tail -f /dev/null; the real command is supplied by start_container.


main.py

Swap from controller import Controller → from backend.zmq_controller import ZmqController (rename local var ctrl).
Replace frontend.show_main_window(...) call with a call into frontend/main_window_ver1.py::show_main_window(client, node_id).


store/models.py + store/globals.py

Add host_mount_consent: bool = False and host_mount_consent_at: str | None = None to GlobalSettings.
Add save_settings(settings: GlobalSettings) -> None in store/globals.py (it currently only has load_settings). Re-export from store/__init__.py. Existing test_store.py::TestLoadSettings still passes; add tests for the new roundtrip.


frontend/__init__.py

Add show_main_window_ver1(client, node_id) that loads the ver1 window. Add a # DEPRECATED: banner above the existing show_main_window noting it targets ver0 and is superseded.


pyproject.toml

Add pyzmq>=26 to runtime deps. Leave fastapi, uvicorn, httpx for now (old path still imports them); mark a TODO to drop in a follow-up.
Add pytest-timeout>=2.3 to dev deps. Add [tool.pytest.ini_options] with markers = ["integration: requires Docker"] and timeout = 60.


controller.py (DEPRECATED)

Prepend module docstring with DEPRECATED — replaced by backend/zmq_controller.py.. No behaviour change.



Files to REUSE AS-IS

backend/pyion_adapter.py — runs inside the container now; no code change.
backend/transfer_backend.py — same, in-container.
backend/backend_facade.py — same, in-container.
backend/startup_checks.py — same.
backend/rc_generator.py — same.
store/*, runtime_logger/*, frontend/SpaceZilla_ver1/* (including *_generated.py), frontend/node_picker.py, frontend/NodePickerDialog.ui.

Implementation order

Pre-flight alignment: read CLAUDE.md (root) end-to-end before writing any code and cross-check every item in this plan against it — coding conventions, forbidden patterns, testing rules, commit style, dependency management, layout rules. If anything in this plan contradicts CLAUDE.md (e.g. module layout, import style, uv vs pip, how ruff is run, whether new top-level packages are allowed), stop and reconcile by editing this plan file first, not the code. Also re-skim docker/README_docker.md so any assumptions about image tag, dockerfile path, and container entrypoint still hold. Only after this alignment pass begin step 1.
backend/ipc/protocol.py → backend/ipc/server.py → backend/ipc/client.py.
backend/ipc/path_map.py + tests/test_path_map.py (pure, no Docker).
backend/container_agent.py.
store/models.py + store/globals.py consent fields + save_settings.
Dockerfile changes + backend/docker_backend.py port-mapping + bind-mount flag + RunningContainer.
backend/zmq_controller.py.
frontend/main_window_ver1.py (incl. consent dialog + revoke menu item) + frontend/__init__.py addition.
main.py swap.
pyproject deps, ruff pass.
Unit tests (non-integration first, then integration), run uv run pytest -m "not integration" then full suite.
Documentation stage (after code + tests are green, before handoff):

Update docker/README_docker.md to reflect the new architecture: container now runs backend.container_agent (REP/PUB on 5555/5556) instead of the old HTTP server; document the two dynamic host-port mappings, the /host:ro,rslave read-only bind mount and what it is for, the consent flow, and the "Revoke host access" Settings item. Remove/replace any mention of uvicorn, httpx, or FastAPI endpoints; if those docs sections still describe the deprecated v0 path, mark them with a > Deprecated blockquote rather than deleting, matching how the code is kept alongside.
Create docker/CONTRIBUTING_docker.md (new file) covering the contributor-facing workflow: how to rebuild the image (docker build -t spacezilla-ion -f docker/pyion_v414a2.dockerfile docker/), how to run the agent locally inside the container for debugging (docker run --rm -it ... python3 -m backend.container_agent --rep-port 5555 --pub-port 5556), how to iterate on backend/ipc/ without rebuilding by using the dev bind mount (-v <repo>/backend:/opt/spacezilla/backend:ro), how to run the integration tests (uv run pytest -m integration, including the spacezilla-test bridge network setup/teardown), the consent toggle for local dev (flip host_mount_consent in settings.json manually), and troubleshooting (port-map parse failures, Windows full-root-mount fallback, docker port output shape). Include a short "adding a new IPC command" recipe keyed to backend/ipc/protocol.py + server.py + client.py.
Cross-link: add a "See also: CONTRIBUTING_docker.md" line in README_docker.md, and a "See also: README_docker.md" line in CONTRIBUTING_docker.md.
Cross-check both docs against CLAUDE.md style rules (heading style, code-fence language tags, line length) before closing the stage.



Verification

uv run pytest tests/ -v -m "not integration" — existing 45 tests + new protocol/client-side unit tests pass (mock the ZMQ socket).
uv run pytest tests/ -v — integration tests run when Docker is available.
Manual: docker build -t spacezilla-ion -f docker/pyion_v414a2.dockerfile docker/ (prebuild), then uv run main.py. Flow: Node Picker → Create New Node → boot → ver1 main window opens → first-send consent dialog → accept → drop a small file into the queue from anywhere under $HOME → PUB events flip status from Running → Completed.
docker ps during run shows spacezilla-<id> with two 127.0.0.1:xxxxx->5555/tcp and 5556/tcp mappings.
docker inspect <id> --format '{{range .Mounts}}{{.Source}}→{{.Destination}} {{.Mode}}{{"\n"}}{{end}}' shows / → /host with ro when consent was granted; absent otherwise.
docker exec spacezilla-<id> ls /SZ_received_files on the receiving node shows the test file.
Toggle "Revoke host access" under SETTINGS → next boot mount is absent → confirm by re-running the inspect command.

Docs-verification checklist (run at end of documentation stage)

grep -R "uvicorn\|httpx\|FastAPI" docker/README_docker.md returns nothing (or only inside a > Deprecated block).
docker/CONTRIBUTING_docker.md exists, passes the same linter/formatter pass that CLAUDE.md prescribes for markdown (if any), and references each of: backend/container_agent.py, backend/ipc/, backend/docker_backend.py, backend/zmq_controller.py, backend/ipc/path_map.py.
Both docs mention the bind-mount + consent flow in the same terms used in code (host_mount_consent, /host, ro,rslave) so a future reader greps once and finds everything.

Out of scope

Deleting FastAPI/httpx/uvicorn from deps (later cleanup).
Removing frontend/SpaceZilla_ver0/ (still loadable through the deprecated path).
Multi-node compose topology (the user picked single-container-per-node; the e2e test spins up two containers directly, not via compose).
Host write-back of received files (container still receives into its own /SZ_received_files; cross-mounting received-files → host is a follow-up, needs a second consent decision).
Sub-path mounts (e.g. "only mount $HOME") — mentioned as a likely future toggle but out of scope for this pass; the current plan is full-root-ro or nothing.
