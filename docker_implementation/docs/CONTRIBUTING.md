# Contributing — How to Add Features to SpaceZilla

This guide shows you which files to edit and how the layers connect. If you're adding a new feature, start here.

## How SpaceZilla is Wired Together

```
┌─────────────────────────────────────────────────────┐
│  One SpaceZilla process                             │
│                                                     │
│  main.py                                            │
│    └── Controller (controller.py)                   │
│          ├── frontend/         ← shows GUI windows  │
│          ├── backend/          ← manages Docker     │
│          ├── store/            ← reads/writes JSON  │
│          └── IPC server        ← FastAPI on 127.0.0.1│
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Key rule:** The controller is the hub. The GUI doesn't call backend functions directly — it goes through the controller's IPC server (HTTP requests to localhost).

## Adding a New GUI Feature

Example: adding a "Check Transfer Status" button.

### Step 1 — Edit the .ui file

Open `frontend/SpaceZilla_ver0/SpaceZilla_ver0.ui` in Qt Designer and add your button/widget.

Then regenerate the Python code:

```bash
pyside6-uic frontend/SpaceZilla_ver0/SpaceZilla_ver0.ui -o frontend/SpaceZilla_ver0/ui_spacezilla.py
```

### Step 2 — Wire the button in spacezilla_main.py

In `frontend/SpaceZilla_ver0/spacezilla_main.py`, connect the button's signal to a handler:

```python
# In __init__:
self.window.btnCheckStatus.clicked.connect(self.check_status)

# New method:
def check_status(self):
    # Call the IPC server to get status from the backend
    import httpx
    response = httpx.get(f"http://127.0.0.1:{self.ipc_port}/transfer-status")
    status = response.json()
    # Update the UI with the result
    self.window.lblStatus.setText(status["message"])
```

### Step 3 — Add an IPC endpoint in controller.py

The GUI calls the controller over HTTP. Add a route to the FastAPI app:

```python
# In controller.py, near the existing /health endpoint:

@ipc_app.get("/transfer-status")
def transfer_status():
    """Return the current transfer status."""
    # Call a backend function, read from store, etc.
    return {"message": "idle", "active_transfers": 0}
```

### Step 4 — Add backend logic if needed

If the feature needs to talk to Docker or ION, add a function in `backend/__init__.py`:

```python
def get_container_stats(container_id: str) -> dict:
    """Get CPU/memory stats for a running container."""
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "json", container_id],
        capture_output=True, text=True,
    )
    return json.loads(result.stdout)
```

Then call it from the IPC endpoint in controller.py.

## Adding a New IPC Endpoint

All IPC endpoints live in `controller.py` on the `ipc_app` FastAPI object.

### GET endpoint (read data)

```python
@ipc_app.get("/queue")
def get_queue():
    """Return the current file transfer queue."""
    # Access controller state or call store/backend functions
    return {"files": [...]}
```

### POST endpoint (trigger an action)

```python
from pydantic import BaseModel

class SendRequest(BaseModel):
    file_path: str
    destination: str

@ipc_app.post("/send")
def send_file(req: SendRequest):
    """Queue a file for transfer."""
    # Trigger backend action
    return {"status": "queued", "file": req.file_path}
```

### Calling it from the GUI

```python
import httpx

# GET
response = httpx.get(f"http://127.0.0.1:{self.ipc_port}/queue")
data = response.json()

# POST
response = httpx.post(
    f"http://127.0.0.1:{self.ipc_port}/send",
    json={"file_path": "/tmp/photo.jpg", "destination": "node-2"},
)
```

## Adding a New Backend Feature

Backend functions live in `backend/__init__.py`. They shell out to the Docker CLI via `subprocess`.

1. Add your function in `backend/__init__.py`
2. Wire it to an IPC endpoint in `controller.py`
3. The GUI calls the endpoint via HTTP

**Logging:** Use `from runtime_logger import get_logger` for status messages — don't use `print()`. The logger writes to both the terminal and `logs/spacezilla.log` with timestamps. See `backend/__init__.py` for the pattern.

Example — restarting a container:

```python
# backend/__init__.py
def restart_container(container_id: str) -> None:
    """Restart a running container."""
    subprocess.run(["docker", "restart", container_id], check=True)
```

```python
# controller.py
@ipc_app.post("/restart")
def restart():
    if ctrl._container_id:
        backend.restart_container(ctrl._container_id)
    return {"status": "restarted"}
```

## Adding New Persistent Data

All data lives as JSON files under `~/.local/share/SpaceZilla/` (or the OS equivalent). The `store/` package handles reading and writing.

### Per-node data

Each node has its own directory: `nodes/{node_id}/`

To add a new per-node file (e.g. `transfers.json`):

1. Add a dataclass in `store/models.py`:
   ```python
   @dataclass
   class TransferLog:
       node_id: str
       transfers: list[dict] = field(default_factory=list)
   ```

2. Add a path helper in `store/paths.py`:
   ```python
   def node_transfers_path(node_id: str) -> Path:
       return node_dir(node_id) / "transfers.json"
   ```

3. Add load/save functions in `store/nodes.py`:
   ```python
   def load_transfers(node_id: str) -> TransferLog:
       path = node_transfers_path(node_id)
       data = json.loads(path.read_text())
       return TransferLog(**data)

   def save_transfers(node_id: str, log: TransferLog) -> None:
       path = node_transfers_path(node_id)
       path.write_text(json.dumps(asdict(log), indent=2) + "\n")
   ```

4. Re-export in `store/__init__.py`

### App-wide data

Global settings live in `global/settings.json`. To add a new global setting, add a field to `GlobalSettings` in `store/models.py`:

```python
@dataclass
class GlobalSettings:
    theme: str = "default"
    log_level: str = "INFO"
    auto_connect: bool = True  # ← new field
```

## Adding a New Node Picker Form Field

The Node Picker form is driven by `store/rc_fields.py`. To add a new field:

1. Add an entry to the `RC_FIELDS` list:
   ```python
   {
       "name": "max_bundle_size",
       "label": "Max Bundle Size (bytes)",
       "type": "int",
       "default": 65536,
   },
   ```

2. The Node Picker automatically picks it up and renders a form input for it.

3. If the value needs to be stored in `NodeConfig`, add a field to the dataclass in `store/models.py` and update `create_node()` in `store/nodes.py` to extract it.

## Quick Reference — How Layers Communicate

| From | To | How | Example |
|------|----|-----|---------|
| GUI button | Controller | HTTP to `127.0.0.1:{port}` | `httpx.get(f"http://127.0.0.1:{port}/health")` |
| Controller | Backend | Direct function call | `backend.start_container(config)` |
| Controller | Store | Direct function call | `store.load_config(node_id)` |
| Controller | Frontend | Direct function call | `frontend.show_main_window(node_id, port)` |
| Frontend | Store | Direct function call | `store.list_nodes()` |
| Controller | New process | `subprocess.Popen` | `ctrl.spawn_peer()` |
| Backend | Docker | `subprocess.run` | `subprocess.run(["docker", "start", ...])` |

## Error Handling

SpaceZilla follows a consistent pattern for handling failures:

- **`controller.boot()` returns a bool.** If anything goes wrong (Docker down, container won't start, etc.), it logs the error, cleans up any partially-started resources via `shutdown()`, and returns `False`. Callers check the return value.

- **Node Picker checks boot results.** If `boot()` returns False, the Node Picker shows a `QMessageBox.warning()` and stays open so the user can try again. If a node was just created and boot fails, the Node Picker deletes it from disk so it doesn't show up as a phantom entry next launch.

- **Docker is checked on startup.** `check_docker_available()` in `node_picker.py` calls `backend.check_docker()` (runs `docker info`). If Docker is down, it prompts the user to start it. If the user declines, Boot/Create buttons are disabled with an error message.

- **When adding new features that can fail:** catch exceptions, clean up partial state, return a success/failure indicator, and surface the error to the user via `QMessageBox`.

- **Don't block the Qt main thread.** Any operation that takes more than ~100ms (Docker builds, network calls, subprocess waits) must run in a `QThread`. Use the `_BootWorker` pattern in `frontend/node_picker.py` as a reference — spawn a `QThread`, show a `QProgressDialog`, and handle the result via a signal. This is why boot doesn't freeze the GUI.

## Dev Troubleshooting

- **Docker image not built** — `docker build -t spacezilla-ion -f docker/pyion_v414a2.dockerfile docker/`
- **Phantom nodes in store** — Delete from `~/.local/share/SpaceZilla/nodes/`
- **Container name conflict** — `docker rm spacezilla-<node_id_prefix>` to remove stale containers
- **"Could not start Docker automatically"** — On Linux, make sure `pkexec` and `systemctl` are available. On macOS/Windows, make sure Docker Desktop is installed.

## Extending ION Configuration

The ionstart.rc file is generated from a template in `backend/rc_generator.py`. To add new ION configuration options:

1. Add a field to `RC_FIELDS` in `store/rc_fields.py` — the New Node form picks it up automatically
2. Add the `{placeholder}` to `_RC_TEMPLATE` in `backend/rc_generator.py`
3. Extract the value in `generate_rc()` and pass it to `.format()`

The template uses the ionstart format documented at https://github.com/nasa-jpl/ION-DTN.

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Just store tests
uv run pytest tests/test_store.py -v

# Just node picker tests
uv run pytest tests/test_node_picker.py -v
```

Tests use temporary directories so they never touch real data. See `tests/conftest.py` for the fixture that makes this work.
