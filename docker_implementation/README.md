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
- **PyION & ION** - Install via (Installation Guide)[https://github.com/NASA-Protocol-Exploits/handbook/blob/main/docs/learning/training/pyion/installing-pyion.md]
- **[uv](https://docs.astral.sh/uv/)** — Python package manager

### Install

```bash
git clone https://github.com/Cal-State-LA-Capstone/SpaceZilla-DTN-OVER-CFDP.git
cd SpaceZilla-DTN-OVER-CFDP
uv sync
```

### Environment Groups

uv manages two dependency groups in `pyproject.toml`:

| Group | What it installs | Command |
|-------|-----------------|---------|
| Runtime | PySide6, FastAPI, uvicorn, httpx, platformdirs, pyion | `uv sync` |
| Dev | ruff (linter), pytest (tests) | `uv sync --only-dev` |

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
3. The controller boots the node: starts a Docker container, starts the IPC server, then opens the main SpaceZilla window
4. From the main window you can queue files for transfer over CFDP

### Spawning additional nodes

Each SpaceZilla process manages exactly one ION node. To run multiple nodes, the GUI spawns a new independent process — each with its own Docker container, IPC server, and window.

### Troubleshooting

- **"Docker Not Running" dialog appears** — Click "Yes" to start Docker automatically. On Linux you'll be asked for your password. On macOS/Windows, Docker Desktop will open.
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

- **test_store.py** (42 tests) — models, paths, node CRUD, settings, themes, rc_fields
- **test_node_picker.py** (3 tests) — Docker health check stub

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

SpaceZilla uses a **per-instance** model: one OS process = one ION node = one GUI window = one IPC server = one on-disk data directory. Additional nodes are spawned as fully independent processes.

### Startup flow

1. `main.py` sets up logging and creates a Qt application
2. A `Controller` is created (manages the lifecycle of one node)
3. The Node Picker dialog is shown
4. User selects or creates a node → `controller.boot(node_id)` is called
5. Controller loads config from disk, starts a Docker container, starts a FastAPI IPC server on a random port, then opens the main SpaceZilla window
6. Qt event loop runs until the user closes the app
7. Controller shuts down: stops IPC server, stops Docker container, writes "stopped" state to disk

### How layers talk to each other

```
GUI (frontend/)
  ↕ direct Python calls
Controller (controller.py)
  ↕ direct Python calls        ↕ direct Python calls
Backend (backend/)              Store (store/)
  ↕ subprocess                    ↕ JSON files
Docker containers               ~/.local/share/SpaceZilla/
```

The GUI talks to the backend **only through the controller's IPC server** (HTTP on 127.0.0.1). The controller calls backend and store functions directly. See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for details on adding features.

## Directory Structure

```
SpaceZilla-DTN-OVER-CFDP/
├── backend/
│   ├── __init__.py          — Docker container management (build, start, stop)
│   ├── fileQueue.py         — CFDP file transfer queue (FileQueue class)
│   └── test_backend.py      — Legacy test harness
├── controller.py            — Central orchestrator (boot, shutdown, spawn_peer)
├── docker/
│   └── pyion_v414a2.dockerfile  — ION + pyion Docker image
├── docs/
│   ├── CONTRIBUTING.md      — Developer guide for adding features
│   └── SDDandSRD.md
├── frontend/
│   ├── __init__.py          — GUI layer (show_node_picker, show_main_window, teardown)
│   ├── node_picker.py       — Node Picker dialog logic
│   ├── NodePickerDialog.ui  — Node Picker Qt Designer file
│   ├── SpaceZilla_ver0/     — Main window UI files and logic
│   │   ├── spacezilla_main.py
│   │   ├── ui_spacezilla.py     — Auto-generated (do not hand-edit)
│   │   ├── SpaceZilla_ver0.ui
│   │   └── ... (dialog .ui files)
│   └── test_frontend.py     — Legacy test harness
├── main.py                  — Entry point (thin launcher)
├── runtime_logger/
│   ├── __init__.py          — Exports: setup_logging, get_logger
│   └── logger.py            — Rotating file + console logging
├── store/                   — On-disk data layer (JSON files)
│   ├── __init__.py          — Re-exports from submodules
│   ├── models.py            — Dataclasses (NodeMeta, NodeConfig, NodeState, etc.)
│   ├── paths.py             — OS-correct path helpers via platformdirs
│   ├── nodes.py             — Per-node CRUD operations
│   ├── globals.py           — App-wide settings and themes
│   └── rc_fields.py         — ionstart.rc form field definitions
├── tests/
│   ├── conftest.py          — Shared fixtures (temp dir for store)
│   ├── test_store.py        — A/B tests for the store package
│   └── test_node_picker.py  — Docker check stub tests
├── pyproject.toml
└── uv.lock
```
