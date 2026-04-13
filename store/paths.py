"""Path helpers for SpaceZilla's on-disk storage layout.

Every function here auto-creates its directory so callers never
have to worry about missing folders. The root comes from
platformdirs so the data lands in the right spot on Linux/macOS/Windows.

Layout on disk:
    <app_data>/
    ├── global/
    │   ├── settings.json
    │   └── themes/
    │       └── <name>.json
    └── nodes/
        └── <node_id>/
            ├── meta.json
            ├── config.json
            └── state.json
"""

from __future__ import annotations

from pathlib import Path

import platformdirs


def app_data_dir() -> Path:
    """Return the platform-correct root data directory for SpaceZilla.

    Uses ``platformdirs.user_data_path("SpaceZilla")``.
    Creates the directory if it does not exist.
    """
    path = platformdirs.user_data_path("SpaceZilla")
    path.mkdir(parents=True, exist_ok=True)
    return path


def global_dir() -> Path:
    """Return ``<app_data>/global/``."""
    path = app_data_dir() / "global"
    path.mkdir(parents=True, exist_ok=True)
    return path


def nodes_dir() -> Path:
    """Return ``<app_data>/nodes/``."""
    path = app_data_dir() / "nodes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def node_dir(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/``."""
    path = nodes_dir() / node_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def node_meta_path(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/meta.json``."""
    return node_dir(node_id) / "meta.json"


def node_config_path(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/config.json``."""
    return node_dir(node_id) / "config.json"


def node_state_path(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/state.json``."""
    return node_dir(node_id) / "state.json"


def settings_path() -> Path:
    """Return ``<app_data>/global/settings.json``."""
    return global_dir() / "settings.json"
