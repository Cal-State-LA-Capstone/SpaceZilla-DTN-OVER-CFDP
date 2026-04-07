"""Typed data models for SpaceZilla node management."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class TransferStatus(enum.Enum):
    """The six transfer statuses used by backend/fileQueue.py."""

    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELED = "Canceled"
    SUSPENDED = "Suspended"


@dataclass
class NodeMeta:
    """Summary info shown in the Node Picker list.

    Stored on disk as nodes/{node_id}/meta.json.
    """

    node_id: str
    name: str
    created_at: str  # ISO-8601
    last_booted: str | None = None


@dataclass
class RcFieldValue:
    """One user-supplied value for an ionstart.rc field."""

    name: str
    value: str | int | bool


@dataclass
class NodeConfig:
    """Full configuration needed to boot a node's Docker container.

    Stored as ``nodes/{node_id}/config.json``.
    """

    node_id: str
    name: str
    ion_node_number: int
    ion_entity_id: int
    bp_endpoint: str
    rc_fields: list[RcFieldValue] = field(default_factory=list)


@dataclass
class NodeState:
    """Runtime state for a booted node (not persistent across restarts).

    Stored as nodes/{node_id}/state.json.
    Written by the controller on boot, cleared on shutdown.
    """

    node_id: str
    pid: int | None = None
    ipc_port: int | None = None
    container_id: str | None = None
    status: str = "stopped"  # "stopped" | "booting" | "running"


@dataclass
class DockerStatus:
    """Result of a Docker availability check."""

    available: bool
    reason: str  # "ok", "missing", "daemon_down", "permission_denied"
    message: str  # human-readable explanation for the UI

    @staticmethod
    def ok() -> DockerStatus:
        """Shortcut for the happy path — Docker is available."""
        return DockerStatus(available=True, reason="ok", message="Docker is ready.")


@dataclass
class GlobalSettings:
    """App-wide settings read once at boot from global/settings.json."""

    theme: str = "default"
    log_level: str = "INFO"
