# Contributing — Docker + ZMQ IPC

Contributor-facing notes for anyone touching `backend/docker_backend.py`,
`backend/container_agent.py`, `backend/ipc/*`, or the Dockerfile.

See also: [../README_docker.md](../README_docker.md).

## Image

The image is `spacezilla-ion`, built from
[`pyion_v414a2.dockerfile`](pyion_v414a2.dockerfile). It contains:

- Ubuntu 22.04 + build tools.
- ION DTN 4.1.4-a.2 compiled from source.
- pyion 4.1.4-a.2 installed with `python3 setup.py install`.
- pyzmq, and the `backend/` + `runtime_logger/` packages baked in at
  `/opt/spacezilla/` (`PYTHONPATH=/opt/spacezilla`).
- Exposes container ports `5555` (REQ/REP) and `5556` (PUB).

### Rebuilding the image

```bash
docker build -t spacezilla-ion -f docker/pyion_v414a2.dockerfile docker/
```

`backend/docker_backend.py::build_image()` does a `docker images -q`
check and skips the build when the tag exists. After changing the
Dockerfile (or anything that lives under `/opt/spacezilla/`), force a
rebuild manually with the command above, or call `build_image(force=True)`
from a Python shell.

### Running the agent by hand for debugging

```bash
docker run --rm -it \
  -p 127.0.0.1:5555:5555 -p 127.0.0.1:5556:5556 \
  -v /:/host:ro,rslave \
  spacezilla-ion \
  bash -c "ionstart -I /home/ionstart.rc && \
           python3 -m backend.container_agent --rep-port 5555 --pub-port 5556"
```

That's the same command `start_container` assembles internally (minus
the per-node environment and generated rc file). Point `IpcClient` at
`127.0.0.1:5555` / `5556` and exercise the facade without the full GUI.

### Dev iteration without rebuilding

Baked code lives at `/opt/spacezilla/backend` inside the image. For
iterative development you can bind-mount your working tree over that
path:

```bash
docker run --rm -it \
  -v "$(pwd)/backend:/opt/spacezilla/backend:ro" \
  -p 127.0.0.1:5555:5555 -p 127.0.0.1:5556:5556 \
  spacezilla-ion bash
```

Changes to `backend/ipc/*.py` or `backend/container_agent.py` take
effect on the next `python3 -m backend.container_agent` without
rebuilding. The host bind mount is still needed for a read-only view of
files you want to `cfdp_send`.

## Testing

### Unit tests (no Docker)

```bash
uv run pytest -m "not integration"
```

Covers `store`, `path_map`, and an in-process `IpcClient` <-> `serve`
roundtrip with a fake facade (`tests/test_ipc_server_client.py`).

### Integration tests (Docker required)

```bash
uv run pytest -m integration
```

The `docker_available` fixture in `tests/conftest.py` runs `docker info`
and `pytest.skip`s the integration suite when the daemon is unreachable
— the suite is therefore safe to run in CI without Docker.

Tests that need a shared bridge network (the end-to-end two-node
transfer in `tests/test_transfer_e2e.py`) create and tear down
`spacezilla-test` themselves. If a previous run crashed and left the
network around, clean up with:

```bash
docker network rm spacezilla-test 2>/dev/null
```

### Toggling `host_mount_consent` for local dev

The consent flag lives in `<platformdirs user data>/SpaceZilla/global/settings.json`:

```json
{ "theme": "default", "log_level": "INFO",
  "host_mount_consent": true, "host_mount_consent_at": "2026-04-23T12:00:00" }
```

Flip `host_mount_consent` by hand to test the "refused consent" branch
without going through the Qt dialog.

## Adding a new IPC command

The protocol is intentionally a small whitelist. To add a command
`do_thing(arg)`:

1. **`backend/backend_facade.py`** — add `BackendFacade.do_thing(arg)`.
   Return JSON-friendly shapes (`dict` / `list` / `str` / `int` /
   `bool` / `None`); tuples are coerced to lists by the server but
   anything more exotic needs to be serialised yourself.
2. **`backend/ipc/protocol.py`** — add `"do_thing"` to the `METHODS`
   frozenset. Without this the server returns `unknown_method`.
3. **`backend/ipc/client.py`** — add a convenience wrapper on `IpcClient`:
   ```python
   def do_thing(self, arg: str) -> ...:
       return self.call("do_thing", arg=arg)
   ```
   Not strictly required — callers can always `client.call("do_thing", arg=arg)` — but the wrapper is cheap and keeps call sites readable.
4. **Tests** — extend `tests/test_ipc_server_client.py::FakeFacade` with
   a stub, and add a case under `TestIpcRoundtrip`.

If the command needs to push asynchronous updates (like `send_files`
does with its PUB events), look at how `backend/ipc/server.py::_dispatch`
special-cases `send_files` to inject an `on_change` callback that
publishes `Event` messages — mirror that pattern.

## Troubleshooting

### `docker port` parse failure

`_resolve_port` in `docker_backend.py` expects lines like
`127.0.0.1:49154` for IPv4 mappings and ignores IPv6 lines. If a
daemon emits an unfamiliar format, `start_container` stops the
container and raises; rerun with `DOCKER_CLI_EXPERIMENTAL=disabled` or
report the raw `docker port <id> 5555/tcp` output.

### Windows full-drive mount

`host_mount=True` tries `-v //./:/host:ro` on Windows. Docker Desktop
doesn't always allow a full-drive mount; when `docker run` fails,
`start_container` logs a warning and retries with `host_mount=False`.
The user then needs to send files from explicitly-shared paths only.

### Container exits immediately

`docker logs <id>` shows the output of the launch command. A common
cause is `ionstart` failing to parse the generated rc file — inspect
`/home/ionstart.rc` inside the container (`docker exec -it <id> cat
/home/ionstart.rc`) and cross-check against `backend/rc_generator.py`.

### `health()` times out during `ZmqController.boot`

The agent takes a few seconds to come up after `ionstart`. The
controller polls for up to 20 seconds (`_HEALTH_TIMEOUT_S`). If it
times out on a slow machine, increase that constant or check `docker
logs` for a Python stacktrace from `backend.container_agent`.
