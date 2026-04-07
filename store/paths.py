"""Path resolution for SpaceZilla on-disk storage.

Uses ``platformdirs`` for OS-correct data directories.
"""

from __future__ import annotations

from pathlib import Path


def app_data_dir() -> Path:
    """Return the platform-correct root data directory for SpaceZilla.

    Uses ``platformdirs.user_data_path("SpaceZilla")``.
    Creates the directory if it does not exist.
    """
    raise NotImplementedError


def global_dir() -> Path:
    """Return ``<app_data>/global/``."""
    raise NotImplementedError


def nodes_dir() -> Path:
    """Return ``<app_data>/nodes/``."""
    raise NotImplementedError


def node_dir(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/``."""
    raise NotImplementedError


def node_meta_path(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/meta.json``."""
    raise NotImplementedError


def node_config_path(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/config.json``."""
    raise NotImplementedError


def node_state_path(node_id: str) -> Path:
    """Return ``<app_data>/nodes/{node_id}/state.json``."""
    raise NotImplementedError


def settings_path() -> Path:
    """Return ``<app_data>/global/settings.json``."""
    raise NotImplementedError
