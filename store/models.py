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
    """Lightweight summary shown in the Node Picker list."""

    node_id: str
    name: str
    created_at: str
    last_booted: str | None = None


@dataclass
class RcFieldValue:
    """One user-supplied value for an ionstart.rc field."""

    name: str
    value: str | int | bool


@dataclass
class NodeConfig:
    """Full configuration needed to boot a node."""

    node_id: str
    name: str
    ion_node_number: int
    ion_entity_id: int
    bp_endpoint: str

    # ADDED: allow multiple nodes on same host without port conflicts
    tcp_port: int = 4556

    rc_fields: list[RcFieldValue] = field(default_factory=list)


@dataclass
class NodeState:
    """Ephemeral runtime state for a booted node."""

    node_id: str
    pid: int | None = None
    ipc_port: int | None = None

    # CHANGED: was "container_id"
    # WHY: no longer using Docker — this now stores the rc file used to start ION
    rc_file_path: str | None = None

    status: str = "stopped"


@dataclass
class DockerStatus:
    """DEPRECATED — kept temporarily for compatibility."""

    available: bool
    reason: str
    message: str


@dataclass
class GlobalSettings:
    """App-wide settings read once at boot."""

    theme: str = "default"
    log_level: str = "INFO"