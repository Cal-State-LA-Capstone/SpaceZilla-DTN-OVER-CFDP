"""Path helpers for SpaceZilla on-disk storage.

Uses platformdirs to pick the right data directory per OS.
"""

from __future__ import annotations

from pathlib import Path


def app_data_dir() -> Path:
    """Root data directory for SpaceZilla (e.g. ~/.local/share/SpaceZilla on Linux).

    Uses platformdirs.user_data_path("SpaceZilla").
    Creates the directory if it doesn't exist.
    """
    raise NotImplementedError


def global_dir() -> Path:
    """<app_data>/global/ — shared settings dir."""
    raise NotImplementedError


def nodes_dir() -> Path:
    """<app_data>/nodes/ — parent dir for all node directories."""
    raise NotImplementedError


def node_dir(node_id: str) -> Path:
    """<app_data>/nodes/{node_id}/ — one node's directory."""
    raise NotImplementedError


def node_meta_path(node_id: str) -> Path:
    """<app_data>/nodes/{node_id}/meta.json."""
    raise NotImplementedError


def node_config_path(node_id: str) -> Path:
    """<app_data>/nodes/{node_id}/config.json."""
    raise NotImplementedError


def node_state_path(node_id: str) -> Path:
    """<app_data>/nodes/{node_id}/state.json."""
    raise NotImplementedError


def settings_path() -> Path:
    """<app_data>/global/settings.json."""
    raise NotImplementedError
