# frontend/queue_button_mapping.py
#
# Wires the SpaceZilla queue UI to the controller's IPC server.
# Follows the architecture: GUI never calls backend directly —
# all transfer operations go through HTTP to 127.0.0.1:{ipc_port}.
#
# It does NOT contain any widget creation or backend logic.
# All widget creation lives in spacezilla_main.py (the UI).
# All transfer logic lives in the IPC server (controller.py).

from __future__ import annotations

import httpx
from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class QueueMapping:
    def __init__(self, ipc_port: int, ui):
        # Save references to the IPC port and UI.
        self.ipc_port = ipc_port
        self.ui = ui

        # Wire UI buttons to controller methods.
        self.ui.file_send.clicked.connect(self.send_action)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.ipc_port}{path}"

    def _is_connected(self) -> bool:
        try:
            response = httpx.get(self._url("/connected"), timeout=2)
            return response.json().get("connected", False)
        except Exception:
            return False

    def send_action(self):
        """
        Called when the file send button is clicked.

        Shows a confirmation dialog, then sends a POST to /queue/send
        on the IPC server to start processing the queue.
        """
        from pathlib import Path
        from frontend.SpaceZilla_ver0.spacezilla_main import load_ui

        if not self.ui.queue_items:
            return

        if not self._is_connected():
            print("Send blocked: backend not connected to ION")
            return

        ui_path = str(Path(__file__).parent / "SpaceZilla_ver0" / "Confirmation_ver0.ui")
        confirm = load_ui(ui_path)
        confirm.setWindowTitle("Confirm")

        if confirm.exec() == QDialog.Accepted:
            try:
                response = httpx.post(self._url("/queue/send"), timeout=5)
                result = response.json()
                if not result.get("ok"):
                    print(f"Send failed: {result.get('msg')}")
            except Exception as e:
                print(f"Send request failed: {e}")
        else:
            print("Send cancelled by user")

    def suspend_action(self, queue_id, status_button, suspend_btn, cancel_btn, resume_btn):
        """Called when a file's suspend button is clicked."""
        try:
            response = httpx.post(self._url("/queue/suspend"), timeout=5)
            result = response.json() if response.content else {}
            if result.get("ok"):
                status_button.setText("Suspended")
        except Exception as e:
            print(f"Suspend request failed: {e}")

    def cancel_action(self, queue_id, status_button, suspend_btn, cancel_btn, resume_btn):
        """Called when a file's cancel button is clicked."""
        try:
            response = httpx.post(self._url("/queue/cancel"), timeout=5)
            result = response.json() if response.content else {}
            if result.get("ok"):
                status_button.setText("Cancelled")
                suspend_btn.setEnabled(False)
                cancel_btn.setEnabled(False)
                resume_btn.setEnabled(False)
        except Exception as e:
            print(f"Cancel request failed: {e}")

    def resume_action(self, queue_id, status_button, suspend_btn, cancel_btn, resume_btn):
        """Called when a file's resume button is clicked."""
        try:
            response = httpx.post(self._url("/queue/resume"), timeout=5)
            result = response.json() if response.content else {}
            if result.get("ok"):
                status_button.setText("Resumed")
        except Exception as e:
            print(f"Resume request failed: {e}")

    def on_status_change(self, queue_id: str, status: str):
        """
        Updates the status button for a queue item.
        Called manually or via future polling — the IPC server
        cannot push callbacks to the frontend.
        """
        status_text = {
            "Queued":    "Pending",
            "Running":   "Sending",
            "Completed": "Done",
            "Failed":    "Failed",
            "Cancelled": "Cancelled",
            "Suspended": "Suspended",
        }
        for item in self.ui.queue_items:
            if item["id"] == queue_id:
                item["status_button"].setText(status_text.get(status, status))
                break

    def add_queue_row(self, queue_id: str, file_path: str) -> None:
        """
        Builds a queue row widget and appends it to the UI queue area.

        Called by _enqueue_file after the backend confirms the file
        has been added to the queue.
        """
        file_name = QFileInfo(file_path).fileName()

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)

        file_label = QLabel(file_name)
        status_button = QPushButton("PENDING")

        suspend_btn = QPushButton()
        cancel_btn = QPushButton()
        resume_btn = QPushButton()

        for btn in [suspend_btn, cancel_btn, resume_btn]:
            btn.setFixedSize(30, 26)

        suspend_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
        cancel_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        resume_btn.setIcon(QIcon.fromTheme("media-playback-start"))

        suspend_btn.clicked.connect(
            lambda: self.suspend_action(queue_id, status_button, suspend_btn, cancel_btn, resume_btn)
        )
        cancel_btn.clicked.connect(
            lambda: self.cancel_action(queue_id, status_button, suspend_btn, cancel_btn, resume_btn)
        )
        resume_btn.clicked.connect(
            lambda: self.resume_action(queue_id, status_button, suspend_btn, cancel_btn, resume_btn)
        )

        row_layout.addWidget(file_label)
        row_layout.addWidget(status_button)
        row_layout.addWidget(suspend_btn)
        row_layout.addWidget(cancel_btn)
        row_layout.addWidget(resume_btn)

        self.ui.queue_layout.addWidget(row_widget)
        self.ui.queue_items.append({
            "id": queue_id,
            "file": file_name,
            "status_button": status_button,
            "widget": row_widget,
        })

    # -----------------------------------------------------------------------
    # Private
    # -----------------------------------------------------------------------

    def enqueue_file(self, file_path: str) -> None:
        """POST to /queue/enqueue and add a row to the UI queue area."""
        try:
            response = httpx.post(
                self._url("/queue/enqueue"),
                json={"paths": [file_path]},
                timeout=5,
            )
            ids = response.json().get("ids", [])
        except Exception as e:
            print(f"Enqueue request failed: {e}")
            return

        if not ids:
            print(f"Enqueue failed for {file_path}")
            return

        self.add_queue_row(queue_id=ids[0], file_path=file_path)
