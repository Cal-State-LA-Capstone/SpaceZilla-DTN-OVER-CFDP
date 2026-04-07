"""Per-node CRUD operations for on-disk storage.

Every write function takes node_id explicitly — a node's process
should only ever read/write its own directory.
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from store.models import NodeConfig, NodeMeta, NodeState, RcFieldValue
from store.paths import node_config_path, node_dir, node_meta_path, node_state_path
from store.paths import nodes_dir as get_nodes_dir


def list_nodes() -> list[NodeMeta]:
    """Scan the nodes/ directory and return a NodeMeta for each one."""
    result: list[NodeMeta] = []
    ndir = get_nodes_dir()
    if not ndir.exists():
        return result
    # Each subfolder in nodes/ is one node. We only care about
    # directories that actually have a meta.json inside.
    for child in sorted(ndir.iterdir()):
        meta_file = child / "meta.json"
        if child.is_dir() and meta_file.exists():
            data = json.loads(meta_file.read_text())
            result.append(NodeMeta(**data))
    return result


def load_meta(node_id: str) -> NodeMeta:
    """Read and return a single node's meta.json."""
    path = node_meta_path(node_id)
    data = json.loads(path.read_text())
    return NodeMeta(**data)


def load_config(node_id: str) -> NodeConfig:
    """Read and return a single node's config.json."""
    path = node_config_path(node_id)
    data = json.loads(path.read_text())
    # rc_fields is stored as a list of plain dicts in JSON,
    # so we need to unpack each one back into an RcFieldValue.
    data["rc_fields"] = [RcFieldValue(**f) for f in data.get("rc_fields", [])]
    return NodeConfig(**data)


def load_state(node_id: str) -> NodeState:
    """Read and return a single node's state.json."""
    path = node_state_path(node_id)
    data = json.loads(path.read_text())
    return NodeState(**data)


def save_meta(node_id: str, meta: NodeMeta) -> None:
    """Write meta.json for the given node."""
    path = node_meta_path(node_id)
    path.write_text(json.dumps(asdict(meta), indent=2) + "\n")


def save_config(node_id: str, config: NodeConfig) -> None:
    """Write config.json for the given node."""
    path = node_config_path(node_id)
    path.write_text(json.dumps(asdict(config), indent=2) + "\n")


def save_state(node_id: str, state: NodeState) -> None:
    """Write state.json for the given node."""
    path = node_state_path(node_id)
    path.write_text(json.dumps(asdict(state), indent=2) + "\n")


def create_node(
    name: str,
    rc_fields: list[RcFieldValue],
) -> str:
    """Create a brand-new node on disk. Returns the generated node_id."""
    node_id = uuid.uuid4().hex
    # node_dir() creates the folder for us as a side effect
    node_dir(node_id)

    # Pull ION-specific values out of the rc_fields list so we can
    # store them as top-level fields in config.json. Fall back to
    # sane defaults if the user didn't provide them.
    rc_lookup = {f.name: f for f in rc_fields}
    ion_node_number = (
        int(rc_lookup["node_number"].value) if "node_number" in rc_lookup else 1
    )
    ion_entity_id = int(rc_lookup["entity_id"].value) if "entity_id" in rc_lookup else 1
    bp_endpoint = (
        str(rc_lookup["bp_endpoint"].value) if "bp_endpoint" in rc_lookup else "ipn:1.1"
    )

    meta = NodeMeta(
        node_id=node_id,
        name=name or f"node-{node_id[:8]}",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    config = NodeConfig(
        node_id=node_id,
        name=meta.name,
        ion_node_number=ion_node_number,
        ion_entity_id=ion_entity_id,
        bp_endpoint=bp_endpoint,
        rc_fields=rc_fields,
    )
    save_meta(node_id, meta)
    save_config(node_id, config)
    return node_id


def delete_node(node_id: str) -> bool:
    """Delete a node folder entirely. Returns True if it existed."""
    ndir = get_nodes_dir() / node_id
    if ndir.exists() and ndir.is_dir():
        shutil.rmtree(ndir)
        return True
    return False
