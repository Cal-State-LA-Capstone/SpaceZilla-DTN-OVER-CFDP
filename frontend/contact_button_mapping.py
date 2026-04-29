from __future__ import annotations

import httpx
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class _ApplyWorker(QThread):
    """Runs apply_contact in a background thread so the GUI stays responsive."""

    finished = Signal(bool, str)

    def __init__(self, url: str, contact_id: str):
        super().__init__()
        self._url = url
        self._contact_id = contact_id

    def run(self):
        try:
            resp = httpx.post(self._url, timeout=90.0)
            data = resp.json()
            self.finished.emit(data.get("ok", False), data.get("msg", ""))
        except Exception as e:
            self.finished.emit(False, str(e))


class ContactMapping:
    def __init__(self, ipc_port: int, ui):
        self.ipc_port = ipc_port
        self.ui = ui
        self._workers: list[_ApplyWorker] = []

        self.ui.add_contact_btn.clicked.connect(self._show_add_dialog)

        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._refresh_contacts)
        self._poll_timer.start(3000)

        self._refresh_contacts()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.ipc_port}{path}"

    def _refresh_contacts(self) -> None:
        try:
            resp = httpx.get(self._url("/contacts"), timeout=2)
            contacts = resp.json().get("contacts", [])
            self._render_contacts(contacts)
        except Exception:
            pass

    def _render_contacts(self, contacts: list[dict]) -> None:
        layout = self.ui.contact_layout
        # Remove existing rows
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for contact in contacts:
            self._add_contact_row(contact)

    def _add_contact_row(self, contact: dict) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel(contact["name"])
        addr_label = QLabel(f"{contact['peer_host']}:{contact['peer_port']}")
        addr_label.setStyleSheet("color: gray; font-size: 11px;")

        connect_btn = QPushButton("Connect")
        delete_btn = QPushButton("X")
        delete_btn.setFixedWidth(28)

        connect_btn.clicked.connect(lambda: self._apply_contact(contact))
        delete_btn.clicked.connect(lambda: self._delete_contact(contact["id"]))

        row_layout.addWidget(name_label)
        row_layout.addWidget(addr_label)
        row_layout.addStretch()
        row_layout.addWidget(connect_btn)
        row_layout.addWidget(delete_btn)

        self.ui.contact_layout.addWidget(row)

    def _apply_contact(self, contact: dict) -> None:
        url = self._url(f"/contacts/{contact['id']}/apply")
        worker = _ApplyWorker(url, contact["id"])

        def _on_done(ok: bool, msg: str):
            if ok:
                self.ui.destination_display.setText(contact["name"])
                print(f"Connected to {contact['name']}: {msg}")
            else:
                print(f"Connect failed for {contact['name']}: {msg}")
            self._workers.discard(worker) if hasattr(self._workers, "discard") else None

        worker.finished.connect(_on_done)
        self._workers.append(worker)
        worker.start()

    def _delete_contact(self, contact_id: str) -> None:
        try:
            httpx.request("DELETE", self._url(f"/contacts/{contact_id}"), timeout=3)
        except Exception as e:
            print(f"Delete contact failed: {e}")
        self._refresh_contacts()

    def _show_add_dialog(self) -> None:
        dialog = QDialog()
        dialog.setWindowTitle("Add Contact")
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        entity_spin = QSpinBox()
        entity_spin.setMaximum(999999)
        entity_spin.setValue(2)
        host_edit = QLineEdit()
        host_edit.setPlaceholderText("e.g. 192.168.1.50")
        port_spin = QSpinBox()
        port_spin.setMaximum(65535)
        port_spin.setValue(1114)

        layout.addRow("Name:", name_edit)
        layout.addRow("Receiver Node Number:", entity_spin)
        layout.addRow("Receiver IP:", host_edit)
        layout.addRow("LTP Port:", port_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        name = name_edit.text().strip()
        host = host_edit.text().strip()
        if not name or not host:
            return

        try:
            httpx.post(
                self._url("/contacts"),
                json={
                    "name": name,
                    "peer_entity_num": entity_spin.value(),
                    "peer_host": host,
                    "peer_port": port_spin.value(),
                },
                timeout=3,
            )
        except Exception as e:
            print(f"Add contact failed: {e}")

        self._refresh_contacts()
