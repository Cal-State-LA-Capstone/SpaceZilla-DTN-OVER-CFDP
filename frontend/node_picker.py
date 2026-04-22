"""Node Picker dialog — first window the user sees.

Lists existing nodes, allows creating new ones, and checks
Docker availability before enabling boot actions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import backend
import store
from PySide6.QtCore import QFile, QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QSpinBox,
)
from store.models import DockerStatus, NodeMeta
from store.rc_fields import RC_FIELDS

if TYPE_CHECKING:
    from collections.abc import Callable


class _BootWorker(QThread):
    """Runs a boot callback in a background thread.

    Emits finished(bool) when done so the GUI can react
    without blocking the Qt event loop.
    """

    finished = Signal(bool)

    def __init__(self, callback, node_id):
        super().__init__()
        self._callback = callback
        self._node_id = node_id

    def run(self):
        result = self._callback(self._node_id)
        self.finished.emit(result)


def check_docker_available() -> DockerStatus:
    """Check if Docker is running; offer to start it if not.

    Calls backend.check_docker() to get the real status. If Docker
    is down, shows a dialog asking the user whether to start it.
    On Linux this triggers a graphical password prompt (pkexec).
    On macOS/Windows it opens Docker Desktop.
    """
    status = backend.docker_backend.check_docker()
    if status.available:
        return status

    reply = QMessageBox.question(
        None,
        "Docker Not Running",
        f"{status.message}\n\nStart Docker now?",
    )
    if reply == QMessageBox.StandardButton.Yes:
        return backend.start_docker()
    return status


def load_node_list() -> list[NodeMeta]:
    """Fetch all nodes from the store for display in the picker."""
    return store.list_nodes()


def open_node_picker(
    *,
    on_select: Callable[[str], None],
    on_create: Callable[[str], None],
) -> None:
    """Create and show the NodePickerDialog.

    Loads NodePickerDialog.ui, populates the node list,
    runs the Docker health check, and wires button signals.
    Boot operations run in a QThread so the GUI stays responsive.

    Args:
        on_select: Called with node_id when user selects a node.
            Must return True on success, False on failure.
        on_create: Called with node_id when user creates a node.
            Must return True on success, False on failure.
    """
    QApplication.instance() or QApplication(sys.argv)

    ui_path = Path(__file__).parent / "NodePickerDialog.ui"
    loader = QUiLoader()
    ui_file = QFile(str(ui_path))
    ui_file.open(QFile.ReadOnly)
    dialog = loader.load(ui_file)
    ui_file.close()

    # Populate the list widget with every saved node
    nodes = load_node_list()
    for node in nodes:
        dialog.listNodes.addItem(f"{node.name}  ({node.node_id[:8]})")

    node_ids = [n.node_id for n in nodes]

    # Docker health check (may prompt to start Docker)
    docker_status = check_docker_available()
    dialog.lblDockerStatus.setText(f"Docker status: {docker_status.message}")

    # -- Boot helper (runs in background thread) -----------------------

    def _start_boot(node_id, callback, cleanup_node_id=None):
        """Launch boot in a QThread with an indeterminate progress bar."""
        progress = QProgressDialog(
            "Starting node (building image if needed)...",
            None,  # no cancel button
            0,
            0,  # indeterminate spinner
            dialog,
        )
        progress.setWindowTitle("Booting Node")
        progress.setMinimumDuration(0)
        progress.show()

        worker = _BootWorker(callback, node_id)

        def _on_done(success):
            progress.close()
            if success:
                dialog.accept()
            else:
                if cleanup_node_id:
                    store.delete_node(cleanup_node_id)
                QMessageBox.warning(
                    dialog,
                    "Boot Failed",
                    "Could not start the node. Check Docker status.",
                )

        worker.finished.connect(_on_done)
        worker.start()
        dialog._boot_worker = worker

    # -- New Node form -------------------------------------------------

    def _show_new_node_form():
        """Show a form for ionstart.rc fields. Returns (name, rc_values) or None."""
        form = QDialog(dialog)
        form.setWindowTitle("Create New Node")
        layout = QFormLayout(form)

        widgets = {}
        for field in RC_FIELDS:
            if field["type"] == "int":
                w = QSpinBox()
                w.setMaximum(999999)
                w.setValue(field["default"])
            elif field["type"] == "bool":
                w = QCheckBox()
                w.setChecked(field["default"])
            else:
                w = QLineEdit()
                w.setText(str(field["default"]))
            layout.addRow(field["label"], w)
            widgets[field["name"]] = w

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(form.accept)
        buttons.rejected.connect(form.reject)
        layout.addRow(buttons)

        if form.exec() != QDialog.DialogCode.Accepted:
            return None

        rc_values = []
        for field in RC_FIELDS:
            w = widgets[field["name"]]
            if field["type"] == "int":
                val = w.value()
            elif field["type"] == "bool":
                val = w.isChecked()
            else:
                val = w.text()
            rc_values.append(store.RcFieldValue(name=field["name"], value=val))

        name_val = next((v for v in rc_values if v.name == "node_name"), None)
        name = str(name_val.value) if name_val and name_val.value else ""
        return name, rc_values

    # -- Signal handlers -----------------------------------------------

    def _on_selection_changed():
        has_selection = dialog.listNodes.currentRow() >= 0
        dialog.btnBootNode.setEnabled(has_selection and docker_status.available)

    def _on_boot_clicked():
        row = dialog.listNodes.currentRow()
        if 0 <= row < len(node_ids):
            _start_boot(node_ids[row], on_select)

    def _on_create_clicked():
        result = _show_new_node_form()
        if result is None:
            return  # user cancelled the form
        name, rc_values = result
        node_id = store.create_node(name=name, rc_fields=rc_values)
        _start_boot(node_id, on_create, cleanup_node_id=node_id)

    # Wire up Qt signals
    dialog.listNodes.currentRowChanged.connect(_on_selection_changed)
    dialog.btnBootNode.clicked.connect(_on_boot_clicked)
    dialog.btnCreateNode.clicked.connect(_on_create_clicked)

    dialog.exec()
