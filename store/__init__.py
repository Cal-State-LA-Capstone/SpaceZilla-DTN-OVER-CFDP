"""store — Pure-function file I/O for SpaceZilla node data.

Every write function takes ``node_id`` explicitly so the
"writes only to own dir" boundary is grep-auditable.
"""

from store.globals import load_settings, load_theme
from store.models import (
    Contact,
    DockerStatus,
    GlobalSettings,
    NodeConfig,
    NodeMeta,
    NodeState,
    RcFieldValue,
    TransferStatus,
)
from store.nodes import (
    create_contact,
    create_node,
    delete_contact,
    delete_node,
    list_nodes,
    load_config,
    load_contacts,
    load_meta,
    load_state,
    save_config,
    save_contacts,
    save_meta,
    save_state,
)
from store.paths import (
    app_data_dir,
    contacts_path,
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
    "DockerStatus",
    "GlobalSettings",
    "NodeConfig",
    "NodeMeta",
    "NodeState",
    "RcFieldValue",
    "TransferStatus",
    "app_data_dir",
    "contacts_path",
    "create_contact",
    "create_node",
    "delete_contact",
    "delete_node",
    "global_dir",
    "list_nodes",
    "load_config",
    "load_contacts",
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
    "save_contacts",
    "save_meta",
    "save_state",
    "settings_path",
]
