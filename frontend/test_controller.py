# frontend/test_controller.py
#
# This controller adapts the simple "message text" UI to the file-based
# backend. The backend sends files over CFDP, so when the user types a
# message we first write it to a temporary file, then queue that file,
# then start queue processing.

from __future__ import annotations

from pathlib import Path
from tkinter import messagebox


class TestController:
    def __init__(self, backend, ui):
        # Save references to the backend and UI.
        self.backend = backend
        self.ui = ui

        # Directory used to hold temporary files created from typed messages.
        self.temp_dir = Path("/tmp/spacezilla_ui_messages")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Wire UI buttons to controller methods.
        self.ui.connect_button.config(command=self.connect_action)
        self.ui.send_button.config(command=self.send_message_action)

    def connect_action(self):
        """
        Called when the Connect button is pressed.

        Reads the local node number from the UI, derives the local BP endpoint,
        and chooses the remote CFDP entity. For this test setup:
            local node = 1
            remote / destination node = 2
            local BP endpoint = ipn:<local>.1

        If the UI has a destination-node entry widget, we use it.
        Otherwise we default to peer entity 2 for the host->container test.
        """
        try:
            node_number = int(self.ui.node_entry.get().strip())

            # Use destination entry if present in the UI; otherwise default to 2.
            if hasattr(self.ui, "dest_entry"):
                entity_id = int(self.ui.dest_entry.get().strip())
            else:
                entity_id = 2

            bp_endpoint = f"ipn:{node_number}.1"

            ok, msg = self.backend.connect(
                node_number=node_number,
                entity_id=entity_id,
                bp_endpoint=bp_endpoint,
            )

            self.ui.status_label.config(text=msg)

            if not ok:
                messagebox.showerror("Connect Failed", msg)

        except ValueError:
            messagebox.showerror(
                "Input Error",
                "Local node number and destination node number must be integers.",
            )

    def send_message_action(self):
        """
        Called when the Send Message button is pressed.

        The backend is file-based, not text-message based, so:
            1. read text from the UI,
            2. write it to a temp file,
            3. queue that file,
            4. start send_files().

        Status updates come back through the backend callback and are shown
        in the status label.
        """
        message = self.ui.message_entry.get().strip()

        if not message:
            messagebox.showwarning("Empty Message", "Please type a message first.")
            return

        if not self.backend.is_connected():
            messagebox.showerror("Not Connected", "Connect before sending a message.")
            return

        try:
            # Use a stable file path for this simple test app.
            # If you want unique names later, switch to timestamped filenames.
            message_file = self.temp_dir / "ui_message.txt"
            message_file.write_text(message, encoding="utf-8")

            # Queue the temp file for CFDP transmission.
            self.backend.queue_files([str(message_file)])

            # Start processing the queue and update UI on status changes.
            ok, msg = self.backend.send_files(on_change=self.on_status_change)

            self.ui.status_label.config(text=msg)

            if not ok:
                messagebox.showerror("Send Failed", msg)
                return

            # Clear message box after successful queue start.
            self.ui.message_entry.delete(0, "end")

        except Exception as e:
            error_msg = f"Failed to prepare/send message file: {e}"
            self.ui.status_label.config(text=error_msg)
            messagebox.showerror("Send Failed", error_msg)

    def on_status_change(self, queue_id: str, status: str):
        """
        Callback invoked by the backend when a queued file changes status.
        """
        self.ui.status_label.config(text=f"{queue_id}: {status}")
