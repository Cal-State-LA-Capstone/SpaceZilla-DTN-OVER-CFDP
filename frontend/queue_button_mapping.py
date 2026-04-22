# frontend/SpaceZilla_ver0/queue_mapping.py
#
# This controller wires the SpaceZilla queue UI to the backend facade.
# It follows the same pattern as TestController:
#   - takes a backend and a ui as arguments
#   - wires UI buttons to controller methods in __init__
#   - uses on_status_change as the backend callback
#
# It does NOT contain any widget creation or backend logic.
# All widget creation lives in spacezilla_main.py (the UI).
# All transfer logic lives in BackendFacade -> TransferBackend.

from __future__ import annotations

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
    def __init__(self, backend, ui):
        # Save references to the backend and UI.
        self.backend = backend
        self.ui = ui

        # Wire UI buttons to controller methods.
        self.ui.file_send.clicked.connect(self.send_action)

    def send_action(self):
        """
        Called when the file send button is clicked.

        Shows a confirmation dialog, then starts processing the queue.
        Status updates come back through the backend callback and are
        reflected on each file's status button in the UI.
        """
        from pathlib import Path
        from frontend.SpaceZilla_ver0.spacezilla_main import load_ui

        if not self.ui.queue_items:
            return

        if not self.backend.is_connected():
            print("Send blocked: backend not connected to ION")
            return

        ui_path = str(Path(__file__).parent / "SpaceZilla_ver0" / "Confirmation_ver0.ui")
        confirm = load_ui(ui_path)
        confirm.setWindowTitle("Confirm")

        if confirm.exec() == QDialog.Accepted:
            ok, msg = self.backend.send_files(on_change=self.on_status_change)
            if not ok:
                print(f"Send failed: {msg}")
        else:
            print("Send cancelled by user")

    def suspend_action(self, queue_id, status_button, suspend_btn, cancel_btn, resume_btn):
        """
        Called when a file's suspend button is clicked.
        """
        ok, msg = self.backend.suspend()
        if ok:
            status_button.setText("Suspended")

    def cancel_action(self, queue_id, status_button, suspend_btn, cancel_btn, resume_btn):
        """
        Called when a file's cancel button is clicked.
        """
        ok, msg = self.backend.cancel()
        if ok:
            status_button.setText("Cancelled")
            suspend_btn.setEnabled(False)
            cancel_btn.setEnabled(False)
            resume_btn.setEnabled(False)

    def resume_action(self, queue_id, status_button, suspend_btn, cancel_btn, resume_btn):
        """
        Called when a file's resume button is clicked.
        """
        ok, msg = self.backend.resume()
        if ok:
            status_button.setText("Resumed")

    def on_status_change(self, queue_id: str, status: str):
        """
        Callback invoked by the backend when a queued file changes status.

        Looks up the matching queue item in the UI and updates its
        status button text.
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
        """Register a file with the backend and add a row to the UI queue area."""
        ids = self.backend.queue_files([file_path])
        if not ids:
            print(f"Enqueue failed for {file_path}")
            return

        queue_id = ids[0]
        self.add_queue_row(queue_id=queue_id, file_path=file_path)
