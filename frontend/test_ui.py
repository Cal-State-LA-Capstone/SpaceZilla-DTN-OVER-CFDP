# frontend/test_ui.py
#
# This file defines the Tkinter widgets only.
# It does NOT contain button logic or backend calls.
# The controller will attach button commands later.
#
# For this test UI, the user enters:
#   - local node number
#   - destination node number
#   - message text
#
# The controller derives the rest of the connection info automatically.

import tkinter as tk


class TestUI:
    def __init__(self):
        # Create the main Tkinter window.
        self.root = tk.Tk()
        self.root.title("SpaceZilla Test UI")

        # -----------------------------
        # Connection input area
        # -----------------------------

        # Local node number label + entry
        tk.Label(self.root, text="Local Node Number").pack()
        self.node_entry = tk.Entry(self.root)
        self.node_entry.insert(0, "1")  # default value for quick testing
        self.node_entry.pack()

        # Destination node number label + entry
        tk.Label(self.root, text="Destination Node Number").pack()
        self.dest_node_entry = tk.Entry(self.root)
        self.dest_node_entry.insert(0, "1")  # default loopback destination
        self.dest_node_entry.pack()

        # Connect button
        # No command is attached here.
        # The controller will attach it.
        self.connect_button = tk.Button(self.root, text="Connect")
        self.connect_button.pack(pady=5)

        # -----------------------------
        # Message input area
        # -----------------------------

        # Message label + entry
        tk.Label(self.root, text="Message").pack()
        self.message_entry = tk.Entry(self.root, width=50)
        self.message_entry.pack(pady=5)

        # Send button
        # No command is attached here.
        # The controller will attach it.
        self.send_button = tk.Button(self.root, text="Send Message")
        self.send_button.pack(pady=5)

        # -----------------------------
        # Status display
        # -----------------------------

        # This label shows the latest app/backend status.
        self.status_label = tk.Label(self.root, text="Not connected")
        self.status_label.pack(pady=10)
