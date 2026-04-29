"""Typed data models for SpaceZilla node management."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class TransferStatus(enum.Enum):
    """Mirror of the six statuses in backend/fileQueue.py."""

    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELED = "Canceled"
    SUSPENDED = "Suspended"


@dataclass
class NodeMeta:
    """Lightweight summary shown in the Node Picker list.

    Stored as ``nodes/{node_id}/meta.json``.
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
    """Ephemeral runtime state for a booted node.

    Stored as ``nodes/{node_id}/state.json``.
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
        """Convenience constructor for the healthy case."""
        return DockerStatus(available=True, reason="ok", message="Docker is ready.")


@dataclass
class Contact:
    """A saved receiver that can be selected from the contacts list.

    Stored as an entry in ``nodes/{node_id}/contacts.json``.
    """

    id: str
    name: str
    peer_entity_num: int
    peer_host: str
    peer_port: int = 1114
    remote_dest_dir: str = "/tmp"


@dataclass
class GlobalSettings:
    """App-wide settings read once at boot from global/settings.json."""

    theme: str = "default"
    log_level: str = "INFO"
