"""store — Pure-function file I/O for SpaceZilla node data.

Every write function takes ``node_id`` explicitly so the
"writes only to own dir" boundary is grep-auditable.
"""

from store.globals import load_settings, load_theme
from store.models import (
    DockerStatus,
    GlobalSettings,
    NodeConfig,
    NodeMeta,
    NodeState,
    RcFieldValue,
    TransferStatus,
)
from store.nodes import (
    create_node,
    delete_node,
    list_nodes,
    load_config,
    load_meta,
    load_state,
    save_config,
    save_meta,
    save_state,
)

# ADDED:
# Export contacts through the store package so they are integrated into the
# datastore surface instead of living as a disconnected module.
from backend.contact_plan import Contact, ContactStore, load_contact_store

from store.paths import (
    app_data_dir,
    global_dir,
    node_config_path,
    node_dir,
    node_meta_path,
    node_state_path,
    nodes_dir,
    settings_path,
)

__all__ = [
    "Contact",
    "ContactStore",
    "DockerStatus",
    "GlobalSettings",
    "NodeConfig",
    "NodeMeta",
    "NodeState",
    "RcFieldValue",
    "TransferStatus",
    "app_data_dir",
    "create_node",
    "delete_node",
    "global_dir",
    "list_nodes",
    "load_config",
    "load_contact_store",
    "load_meta",
    "load_settings",
    "load_state",
    "load_theme",
    "node_config_path",
    "node_dir",
    "node_meta_path",
    "node_state_path",
    "nodes_dir",
    "save_config",
    "save_meta",
    "save_state",
    "settings_path",
]