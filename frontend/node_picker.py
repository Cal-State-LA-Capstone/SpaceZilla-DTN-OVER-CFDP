"""Node Picker dialog — first window the user sees.

Lists existing nodes, allows creating new ones, and checks
Docker availability before enabling boot actions.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import backend
import store
from backend.rc_generator import generate_receiver_rc
from PySide6.QtCore import QFile, QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
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
    status = backend.check_docker()
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


def _get_local_ips() -> list[str]:
    """Return all non-loopback IPv4 addresses visible to this process."""
    import ipaddress

    seen: set[str] = set()
    results: list[str] = []

    def _add(ip: str) -> None:
        try:
            if not ipaddress.ip_address(ip).is_loopback and ip not in seen:
                seen.add(ip)
                results.append(ip)
        except ValueError:
            pass

    try:
        with socket.create_connection(("8.8.8.8", 80), timeout=2) as s:
            _add(s.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            _add(info[4][0])
    except OSError:
        pass

    return results


def _show_receiver_config_dialog(node_id: str, parent=None) -> None:
    """Show a dialog with a pre-filled receiver.rc the user can save or copy."""
    config = store.load_config(node_id)
    if config is None:
        QMessageBox.warning(parent, "Error", "Could not load node config.")
        return

    dialog = QDialog(parent)
    dialog.setWindowTitle("Receiver Config")
    dialog.resize(520, 420)
    layout = QVBoxLayout(dialog)

    layout.addWidget(
        QLabel("Sender IP (your LAN or public IP — must be reachable by the receiver):")
    )
    ip_combo = QComboBox()
    ip_combo.setEditable(True)
    detected = _get_local_ips()
    for ip in detected:
        ip_combo.addItem(ip)
    ip_combo.setCurrentText(detected[0] if detected else "")
    ip_combo.lineEdit().setPlaceholderText(
        "e.g. 192.168.1.118 (LAN) or 203.0.113.5 (WAN)"
    )
    layout.addWidget(ip_combo)

    hint = QLabel(
        "LAN (same network): use your Wi-Fi/Ethernet IP (e.g. 192.168.1.x).\n"
        "WAN (different networks): use your public IP — find it at whatismyip.com.\n"
        "On WSL2: run  ipconfig  in Windows PowerShell and use your Wi-Fi IPv4 address."
    )
    hint.setWordWrap(True)
    hint.setStyleSheet("color: gray; font-size: 11px;")
    layout.addWidget(hint)

    preview = QPlainTextEdit()
    preview.setReadOnly(True)
    preview.setFont(preview.document().defaultFont())
    layout.addWidget(preview)

    def _refresh():
        try:
            content = generate_receiver_rc(config, ip_combo.currentText().strip())
            preview.setPlainText(content)
        except Exception as exc:
            preview.setPlainText(f"Error: {exc}")

    _refresh()
    ip_combo.editTextChanged.connect(lambda _: _refresh())

    btn_row = QDialogButtonBox()
    btn_save = QPushButton("Save to File")
    btn_copy = QPushButton("Copy to Clipboard")
    btn_close = QPushButton("Close")
    btn_row.addButton(btn_save, QDialogButtonBox.ButtonRole.ActionRole)
    btn_row.addButton(btn_copy, QDialogButtonBox.ButtonRole.ActionRole)
    btn_row.addButton(btn_close, QDialogButtonBox.ButtonRole.RejectRole)
    layout.addWidget(btn_row)

    def _save():
        if not ip_combo.currentText().strip():
            QMessageBox.warning(
                dialog, "Missing IP", "Enter the sender's LAN IP before saving."
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Save Receiver Config",
            "receiver.rc",
            "RC files (*.rc);;All files (*)",
        )
        if path:
            with open(path, "w") as f:
                f.write(preview.toPlainText())

    def _copy():
        if not ip_combo.currentText().strip():
            QMessageBox.warning(
                dialog, "Missing IP", "Enter the sender's LAN IP before copying."
            )
            return
        QApplication.clipboard().setText(preview.toPlainText())

    btn_save.clicked.connect(_save)
    btn_copy.clicked.connect(_copy)
    btn_close.clicked.connect(dialog.reject)

    dialog.exec()


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
        dialog.btnReceiverConfig.setEnabled(has_selection)

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

    def _on_receiver_config_clicked():
        row = dialog.listNodes.currentRow()
        if 0 <= row < len(node_ids):
            _show_receiver_config_dialog(node_ids[row], parent=dialog)

    # Wire up Qt signals
    dialog.listNodes.currentRowChanged.connect(_on_selection_changed)
    dialog.btnBootNode.clicked.connect(_on_boot_clicked)
    dialog.btnCreateNode.clicked.connect(_on_create_clicked)
    dialog.btnReceiverConfig.clicked.connect(_on_receiver_config_clicked)

    dialog.exec()
