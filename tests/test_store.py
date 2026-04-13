"""A/B tests for the store/ package.

Each test sets up an expected value (A), runs the code to get
an actual value (B), then asserts A == B.
"""

import json

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
    save_state,
)
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
from store.rc_fields import RC_FIELDS

# ── store/models.py ──────────────────────────────────────────────


class TestTransferStatus:
    def test_values(self):
        expected = {"Queued", "Running", "Completed", "Failed", "Canceled", "Suspended"}
        actual = {s.value for s in TransferStatus}
        assert actual == expected

    def test_count(self):
        expected = 6
        actual = len(TransferStatus)
        assert actual == expected


class TestDockerStatus:
    def test_ok_available(self):
        expected = True
        actual = DockerStatus.ok().available
        assert actual == expected

    def test_ok_reason(self):
        expected = "ok"
        actual = DockerStatus.ok().reason
        assert actual == expected


class TestNodeMeta:
    def test_last_booted_defaults_to_none(self):
        expected = None
        meta = NodeMeta(node_id="abc", name="test", created_at="2026-01-01")
        actual = meta.last_booted
        assert actual == expected


class TestNodeState:
    def test_status_default(self):
        expected = "stopped"
        actual = NodeState(node_id="abc").status
        assert actual == expected

    def test_pid_default(self):
        expected = None
        actual = NodeState(node_id="abc").pid
        assert actual == expected

    def test_ipc_port_default(self):
        expected = None
        actual = NodeState(node_id="abc").ipc_port
        assert actual == expected


class TestNodeConfig:
    def test_rc_fields_default_empty(self):
        expected = []
        actual = NodeConfig(
            node_id="abc",
            name="test",
            ion_node_number=1,
            ion_entity_id=1,
            bp_endpoint="ipn:1.1",
        ).rc_fields
        assert actual == expected


class TestGlobalSettings:
    def test_theme_default(self):
        expected = "default"
        actual = GlobalSettings().theme
        assert actual == expected

    def test_log_level_default(self):
        expected = "INFO"
        actual = GlobalSettings().log_level
        assert actual == expected


# ── store/paths.py ───────────────────────────────────────────────


class TestPaths:
    def test_app_data_dir_creates_directory(self):
        expected = True
        actual = app_data_dir().is_dir()
        assert actual == expected

    def test_nodes_dir_creates_directory(self):
        expected = True
        actual = nodes_dir().is_dir()
        assert actual == expected

    def test_node_dir_creates_directory(self):
        expected = True
        actual = node_dir("test-node").is_dir()
        assert actual == expected

    def test_global_dir_creates_directory(self):
        expected = True
        actual = global_dir().is_dir()
        assert actual == expected

    def test_node_meta_path_filename(self):
        expected = "meta.json"
        actual = node_meta_path("x").name
        assert actual == expected

    def test_node_config_path_filename(self):
        expected = "config.json"
        actual = node_config_path("x").name
        assert actual == expected

    def test_node_state_path_filename(self):
        expected = "state.json"
        actual = node_state_path("x").name
        assert actual == expected

    def test_settings_path_under_global(self):
        expected = True
        actual = "global" in settings_path().parts
        assert actual == expected


# ── store/nodes.py ───────────────────────────────────────────────


def _make_rc_fields():
    """Helper — builds a default set of RcFieldValues for testing."""
    return [
        RcFieldValue(name="node_number", value=1),
        RcFieldValue(name="entity_id", value=1),
        RcFieldValue(name="bp_endpoint", value="ipn:1.1"),
        RcFieldValue(name="node_name", value="test-node"),
        RcFieldValue(name="service_count", value=1),
    ]


class TestCreateNode:
    def test_returns_uuid_hex_length(self):
        expected = 32
        node_id = create_node("test-node", _make_rc_fields())
        actual = len(node_id)
        assert actual == expected

    def test_returns_valid_hex(self):
        node_id = create_node("test-node", _make_rc_fields())
        # Should not raise ValueError — valid hex
        int(node_id, 16)

    def test_writes_meta_file(self):
        expected = True
        node_id = create_node("test-node", _make_rc_fields())
        actual = node_meta_path(node_id).exists()
        assert actual == expected

    def test_writes_config_file(self):
        expected = True
        node_id = create_node("test-node", _make_rc_fields())
        actual = node_config_path(node_id).exists()
        assert actual == expected


class TestLoadMetaRoundtrip:
    def test_name_matches(self):
        expected = "test-node"
        node_id = create_node("test-node", _make_rc_fields())
        actual = load_meta(node_id).name
        assert actual == expected

    def test_node_id_matches(self):
        node_id = create_node("test-node", _make_rc_fields())
        expected = node_id
        actual = load_meta(node_id).node_id
        assert actual == expected


class TestLoadConfigRoundtrip:
    def test_ion_node_number(self):
        expected = 1
        node_id = create_node("test-node", _make_rc_fields())
        actual = load_config(node_id).ion_node_number
        assert actual == expected

    def test_bp_endpoint(self):
        expected = "ipn:1.1"
        node_id = create_node("test-node", _make_rc_fields())
        actual = load_config(node_id).bp_endpoint
        assert actual == expected

    def test_rc_fields_reconstructed(self):
        expected = 5
        node_id = create_node("test-node", _make_rc_fields())
        actual = len(load_config(node_id).rc_fields)
        assert actual == expected

    def test_rc_field_types(self):
        """Each rc_field should be an RcFieldValue, not a plain dict."""
        node_id = create_node("test-node", _make_rc_fields())
        config = load_config(node_id)
        expected = True
        actual = all(isinstance(f, RcFieldValue) for f in config.rc_fields)
        assert actual == expected


class TestSaveAndLoadState:
    def test_status_roundtrip(self):
        expected = "running"
        node_id = create_node("test-node", _make_rc_fields())
        save_state(node_id, NodeState(node_id=node_id, status="running", ipc_port=8080))
        actual = load_state(node_id).status
        assert actual == expected

    def test_ipc_port_roundtrip(self):
        expected = 8080
        node_id = create_node("test-node", _make_rc_fields())
        save_state(node_id, NodeState(node_id=node_id, status="running", ipc_port=8080))
        actual = load_state(node_id).ipc_port
        assert actual == expected


class TestListNodes:
    def test_empty(self):
        expected = []
        actual = list_nodes()
        assert actual == expected

    def test_finds_created_nodes(self):
        expected = 2
        create_node("node-a", _make_rc_fields())
        create_node("node-b", _make_rc_fields())
        actual = len(list_nodes())
        assert actual == expected


class TestDeleteNode:
    def test_delete_returns_true(self):
        expected = True
        node_id = create_node("test-node", _make_rc_fields())
        actual = delete_node(node_id)
        assert actual == expected

    def test_delete_removes_from_list(self):
        expected = 0
        node_id = create_node("test-node", _make_rc_fields())
        delete_node(node_id)
        actual = len(list_nodes())
        assert actual == expected

    def test_delete_nonexistent(self):
        expected = False
        actual = delete_node("this-id-does-not-exist")
        assert actual == expected


# ── store/globals.py ─────────────────────────────────────────────


class TestLoadSettings:
    def test_defaults_when_no_file(self):
        expected = ("default", "INFO")
        settings = load_settings()
        actual = (settings.theme, settings.log_level)
        assert actual == expected

    def test_reads_from_file(self):
        expected = "dark"
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"theme": "dark", "log_level": "DEBUG"}))
        actual = load_settings().theme
        assert actual == expected


class TestLoadTheme:
    def test_missing_returns_empty_dict(self):
        expected = {}
        actual = load_theme("nonexistent")
        assert actual == expected

    def test_reads_from_file(self):
        expected = {"bg": "#000", "fg": "#fff"}
        themes_dir = global_dir() / "themes"
        themes_dir.mkdir(parents=True, exist_ok=True)
        (themes_dir / "dark.json").write_text(json.dumps(expected))
        actual = load_theme("dark")
        assert actual == expected


# ── store/rc_fields.py ───────────────────────────────────────────


class TestRcFields:
    def test_count(self):
        expected = 5
        actual = len(RC_FIELDS)
        assert actual == expected

    def test_required_keys(self):
        expected = {"name", "label", "type", "default"}
        for field in RC_FIELDS:
            actual = set(field.keys())
            assert actual == expected, f"Field {field.get('name')} has wrong keys"
