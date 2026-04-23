# SpaceZilla-DTN-OVER-CFDP

A PySide6 GUI application for managing DTN (Delay-Tolerant Networking) file transfers using CFDP (CCSDS File Delivery Protocol) over ION (Interplanetary Overlay Network).

dev branch naming convention:
`feature/*` - new feature
`fix/*` - bug fixes
`chore/*` - maintenance, config, tooling
`docs/` - documentation only

## Getting Started

### Prerequisites

- **Python 3.13+**
- **Docker** — each node runs ION inside a container
- **[uv](https://docs.astral.sh/uv/)** — Python package manager

### Install

```bash
git clone https://github.com/Cal-State-LA-Capstone/SpaceZilla-DTN-OVER-CFDP.git
cd SpaceZilla-DTN-OVER-CFDP
uv sync
```

### Docker Setup (one-time)

After installing Docker, add your user to the `docker` group so SpaceZilla can manage containers without needing root:

```bash
sudo usermod -aG docker $USER
```

**Log out and log back in** (or reboot) for the change to take effect. Verify it worked:

```bash
docker info
```

If it prints server info without "permission denied", you're good. SpaceZilla will auto-start the Docker daemon if it's not running.

### Environment Groups

uv manages two dependency groups in `pyproject.toml`:

| Group | What it installs | Command |
|-------|-----------------|---------|
| Runtime | PySide6, pyzmq, pyion, platformdirs | `uv sync` |
| Dev | ruff (linter), pytest, pytest-timeout | `uv sync --only-dev` |

> **Deprecated:** The runtime list also includes `fastapi`, `uvicorn`, and `httpx`. They survive from the pre-ZMQ HTTP-IPC path (`controller.py`) and are slated for removal in a follow-up once nothing imports them.

To install everything (runtime + dev):

```bash
uv sync && uv sync --only-dev
```

To install dev tools only (for linting/testing without runtime deps):

```bash
uv sync --only-dev
```

## How to Use

### Run the app

```bash
uv run main.py
```


### What happens

1. The **Node Picker** dialog appears — this is the first screen you see
2. Pick an existing node or click **Create New Node** to make one
3. `ZmqController.boot()` runs:
   - builds the `spacezilla-ion` image if needed,
   - starts a Docker container with the pyion-backend agent on fixed container ports `5555` (REQ/REP) and `5556` (PUB), published to ephemeral `127.0.0.1:<port>` host mappings,
   - opens a ZMQ `IpcClient` and polls `health()` until the in-container agent is ready.
4. The ver1 main window opens. On the first boot you get a one-time dialog asking whether the container can read your host files at `/host:ro`. Consent is stored in `GlobalSettings.host_mount_consent` and can be revoked later from **Settings > Revoke host access**.
5. Double-click a file in the source tree, press the send button, and the host path is translated (`/home/alice/x.jpg` -> `/host/home/alice/x.jpg`) and passed to the in-container backend for CFDP transfer.

### Spawning additional nodes

Each SpaceZilla process manages exactly one ION node. To run multiple nodes, the GUI spawns a new independent process — each with its own Docker container, IPC server, and window.

### Troubleshooting

- **"Docker Not Running" dialog appears** — Click "Yes" to start Docker automatically. On Linux you'll be asked for your password. On macOS/Windows, Docker Desktop will open.
- **Docker Desktop won't start** — Make sure Docker is installed. See https://docs.docker.com/get-docker/
- **"Boot Failed" warning** — Docker may be running but the ION image isn't built yet. Ask a team member or check [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for dev setup steps.
- **Process won't exit after closing the window** — Press Ctrl+C in the terminal.

## How to Test

### Run all tests

```bash
uv run pytest tests/ -v
```

### Run a specific test file

```bash
uv run pytest tests/test_store.py -v
```

### What the tests cover

- **test_store.py** — models, paths, node CRUD, settings (including `host_mount_consent`), themes, rc_fields.
- **test_node_picker.py** — Docker health check stub.
- **test_path_map.py** — pure host <-> container path translation.
- **test_ipc_server_client.py** — in-process ZMQ server + client smoke tests using a fake backend facade.
- **test_docker_backend_integration.py**, **test_host_mount.py**, **test_ipc_roundtrip.py**, **test_transfer_e2e.py** — marked with `integration`; skipped unless a real Docker daemon is reachable. Run the full suite with `uv run pytest` (the conftest fixture `docker_available` auto-skips when there's no daemon).

Tests use `tmp_path` so they never touch your real data directory. Each test gets a clean, isolated temp folder.

## Linting

```bash
# Check for errors
uv run ruff check .

# Auto-fix what it can
uv run ruff check . --fix

# Check formatting
uv run ruff format --check .

# Auto-format
uv run ruff format .
```

## Architecture

SpaceZilla uses a **per-instance** model: one OS process = one ION node = one GUI window = one IPC client/server pair = one on-disk data directory. Additional nodes are spawned as fully independent processes.

### Startup flow

1. `main.py` sets up logging and creates a Qt application.
2. A `ZmqController` is created (see `backend/zmq_controller.py`).
3. The Node Picker dialog is shown.
4. User selects or creates a node -> `ZmqController.boot(node_id)`:
   - loads the node config from `store/`,
   - builds the `spacezilla-ion` image if missing,
   - reads `GlobalSettings.host_mount_consent` and starts the container with or without the `-v /:/host:ro,rslave` bind mount accordingly,
   - resolves the two ephemeral `127.0.0.1` host ports assigned by Docker for container ports 5555 / 5556 via `docker port`,
   - creates an `IpcClient` and polls `health()` until the in-container `backend.container_agent` is ready (20 s budget).
5. The ver1 main window opens. Qt event loop runs until the user closes the window.
6. `ZmqController.shutdown()` closes the IPC client, stops the container, and marks the node `stopped` on disk.

### How layers talk to each other

```
GUI (frontend/SpaceZilla_ver1/ + main_window_ver1.py)
   |                                       ^
   | IpcClient.call(REQ/REP)                | Qt queued signal
   v                                       |
+-------------------------- host -----------+--------------------------+
| ZmqController + IpcClient (ZMQ: tcp://127.0.0.1:<rep>, tcp://...<pub>)|
+---------------------------+-------------------------------------------+
                            | docker run / docker stop
                            v
+-------------------------- container ------------------------------+
|  ionstart -> backend.container_agent                              |
|    +-- backend.ipc.server.serve (REP :5555, PUB :5556)           |
|    +-- backend.backend_facade.BackendFacade                       |
|          +-- TransferBackend (pyion, CFDP, event handlers)        |
+-------------------------------------------------------------------+

Store (store/)                     Disk
  ^ JSON files                      ~/.local/share/SpaceZilla/
```

The GUI talks to the backend **only through `IpcClient`** — REQ/REP for commands and a PUB subscription for per-transfer status updates. The in-container agent owns the only pyion process and therefore the only process that can speak to ION.

The host bind mount (`/` -> `/host:ro,rslave`) lets pyion `cfdp_send` files in place without any pre-transfer copy. Every host path crossing the IPC boundary is rewritten with `backend.ipc.path_map.to_container_path` (for example `/home/alice/x.jpg` becomes `/host/home/alice/x.jpg`). The mount is always read-only and only applied when `GlobalSettings.host_mount_consent` is true.

See [docker/CONTRIBUTING_docker.md](docker/CONTRIBUTING_docker.md) for how to iterate on the container + IPC code.

> **Deprecated:** The original host-side `Controller` (`controller.py`) ran a FastAPI/uvicorn IPC server on 127.0.0.1 and called pyion directly on the host. pyion needs to share a process tree with `ionstart`, which is only true inside the container, so the FastAPI path cannot actually complete a CFDP transfer. `controller.py` is kept alongside the new `ZmqController` during the transition; do not build new features against it.

## Directory Structure

```
SpaceZilla-DTN-OVER-CFDP/
├── backend/
│   ├── __init__.py          — Re-exports docker_backend helpers (build_image, start_container, ...)
│   ├── docker_backend.py    — docker run / stop, port resolution, host bind mount
│   ├── zmq_controller.py    — Per-process lifecycle: boot, shutdown, health polling
│   ├── container_agent.py   — In-container entry point (python3 -m backend.container_agent)
│   ├── backend_facade.py    — Stable surface area exposed over IPC
│   ├── transfer_backend.py  — CFDP queue + event handler plumbing
│   ├── pyion_adapter.py     — pyion calls (BP open, CFDP send, event registration)
│   ├── startup_checks.py    — pyion import + environment sanity checks
│   ├── rc_generator.py      — ionstart.rc generation from NodeConfig
│   ├── ipc/
│   │   ├── protocol.py      — Request/Reply/Event schemas + method whitelist
│   │   ├── server.py        — REP + PUB server run inside the container
│   │   ├── client.py        — Host-side IpcClient (REQ + SUB)
│   │   └── path_map.py      — host <-> container path translation
│   └── fileQueue.py         — (legacy) CFDP transfer queue
├── controller.py            — DEPRECATED — replaced by backend/zmq_controller.py
├── docker/
│   ├── pyion_v414a2.dockerfile — ION + pyion + backend agent image
│   └── CONTRIBUTING_docker.md  — Contributor workflow for the container + IPC code
├── docs/
│   ├── CONTRIBUTING.md
│   └── SDDandSRD.md
├── frontend/
│   ├── __init__.py          — show_node_picker, show_main_window_ver1, teardown
│   ├── main_window_ver1.py  — Host-side glue, consent dialog, PUB -> Qt signal bridge
│   ├── node_picker.py       — Node Picker dialog logic
│   ├── NodePickerDialog.ui
│   ├── SpaceZilla_ver0/     — DEPRECATED UI (still loadable via show_main_window)
│   └── SpaceZilla_ver1/     — Current UI (theming, dialogs, file-filter tree)
├── main.py                  — Entry point (ZmqController + ver1 window)
├── runtime_logger/
│   ├── __init__.py          — Exports: setup_logging, get_logger
│   └── logger.py
├── store/                   — On-disk data layer (JSON files)
│   ├── __init__.py
│   ├── models.py            — NodeMeta, NodeConfig, NodeState, GlobalSettings (host_mount_consent)
│   ├── paths.py
│   ├── nodes.py
│   ├── globals.py           — load_settings, save_settings, load_theme
│   └── rc_fields.py
├── tests/
│   ├── conftest.py          — store_dir + docker_available fixtures
│   ├── test_store.py
│   ├── test_node_picker.py
│   ├── test_path_map.py
│   ├── test_ipc_server_client.py
│   ├── test_docker_backend_integration.py  (integration)
│   ├── test_host_mount.py                  (integration)
│   ├── test_ipc_roundtrip.py               (integration)
│   └── test_transfer_e2e.py                (integration, skipped)
├── pyproject.toml
└── uv.lock
```

See also: [docker/CONTRIBUTING_docker.md](docker/CONTRIBUTING_docker.md).
