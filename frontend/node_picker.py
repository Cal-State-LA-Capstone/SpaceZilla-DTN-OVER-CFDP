"""Node Picker dialog — first window the user sees.

Lists existing nodes, allows creating new ones, and checks
Docker availability before enabling boot actions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import store
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication
from store.models import DockerStatus, NodeMeta
from store.rc_fields import RC_FIELDS

if TYPE_CHECKING:
    from collections.abc import Callable


def check_docker_available() -> DockerStatus:
    """Verify Docker is installed, daemon is running, and accessible.

    TODO(teammate): implement real checks. Currently returns OK.
    """
    return DockerStatus.ok()


def load_node_list() -> list[NodeMeta]:
    """Fetch all nodes from the store for display in the picker."""
    return store.list_nodes()


def open_node_picker(
    *,
    on_select: Callable[[str], None],
    on_create: Callable[[str], None],
) -> None:
    """Instantiate and show the NodePickerDialog.

    Loads ``NodePickerDialog.ui``, populates the node list,
    runs the Docker health check, and wires button signals.

    Args:
        on_select: Called with ``node_id`` when user selects a node.
        on_create: Called with ``node_id`` when user creates a node.
    """
    # Make sure we have a QApplication (reuse one if it already exists)
    QApplication.instance() or QApplication(sys.argv)

    # Load the dialog layout from the .ui file created in Qt Designer
    ui_path = Path(__file__).parent / "NodePickerDialog.ui"
    loader = QUiLoader()
    from PySide6.QtCore import QFile

    ui_file = QFile(str(ui_path))
    ui_file.open(QFile.ReadOnly)
    dialog = loader.load(ui_file)
    ui_file.close()

    # Populate the list widget with every saved node
    nodes = load_node_list()
    for node in nodes:
        dialog.listNodes.addItem(f"{node.name}  ({node.node_id[:8]})")

    # Keep a parallel list of IDs so we can map row index -> node_id
    node_ids = [n.node_id for n in nodes]

    # Show Docker health in the status label
    docker_status = check_docker_available()
    dialog.lblDockerStatus.setText(f"Docker status: {docker_status.message}")

    def _on_selection_changed():
        # Only enable the Boot button if something is selected AND Docker is up
        has_selection = dialog.listNodes.currentRow() >= 0
        dialog.btnBootNode.setEnabled(has_selection and docker_status.available)

    def _on_boot_clicked():
        row = dialog.listNodes.currentRow()
        if 0 <= row < len(node_ids):
            on_select(node_ids[row])
            dialog.accept()

    def _on_create_clicked():
        # Use the default values from RC_FIELDS to create a quick node
        rc_values = [
            store.RcFieldValue(name=f["name"], value=f["default"]) for f in RC_FIELDS
        ]
        name_field = next((f for f in rc_values if f.name == "node_name"), None)
        name = str(name_field.value) if name_field and name_field.value else ""
        node_id = store.create_node(name=name, rc_fields=rc_values)
        on_create(node_id)
        dialog.accept()

    # Wire up Qt signals to our handler functions
    dialog.listNodes.currentRowChanged.connect(_on_selection_changed)
    dialog.btnBootNode.clicked.connect(_on_boot_clicked)
    dialog.btnCreateNode.clicked.connect(_on_create_clicked)

    dialog.exec()
