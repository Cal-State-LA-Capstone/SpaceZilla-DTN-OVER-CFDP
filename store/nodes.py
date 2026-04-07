"""Per-node CRUD operations for on-disk storage.

Every write function takes ``node_id`` explicitly so the
"writes only to own dir" boundary is grep-auditable.
"""

from __future__ import annotations

from store.models import NodeConfig, NodeMeta, NodeState, RcFieldValue


def list_nodes() -> list[NodeMeta]:
    """Return metadata for every node on disk.

    Reads ``meta.json`` from each subdirectory under ``nodes/``.
    """
    raise NotImplementedError


def load_meta(node_id: str) -> NodeMeta:
    """Read and return a single node's meta.json."""
    raise NotImplementedError


def load_config(node_id: str) -> NodeConfig:
    """Read and return a single node's config.json."""
    raise NotImplementedError


def load_state(node_id: str) -> NodeState:
    """Read and return a single node's state.json."""
    raise NotImplementedError


def save_meta(node_id: str, meta: NodeMeta) -> None:
    """Write meta.json for the given node."""
    raise NotImplementedError


def save_config(node_id: str, config: NodeConfig) -> None:
    """Write config.json for the given node."""
    raise NotImplementedError


def save_state(node_id: str, state: NodeState) -> None:
    """Write state.json for the given node."""
    raise NotImplementedError


def create_node(
    name: str,
    rc_fields: list[RcFieldValue],
) -> str:
    """Create a new node directory with meta.json and config.json.

    Returns the generated ``node_id`` (a UUID4 hex string).
    """
    raise NotImplementedError


def delete_node(node_id: str) -> bool:
    """Remove a node's directory from disk.

    Returns True if the node existed and was deleted.
    """
    raise NotImplementedError
