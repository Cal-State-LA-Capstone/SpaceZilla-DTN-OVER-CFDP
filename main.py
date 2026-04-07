"""Entry point for SpaceZilla.

This is the thin launcher that wires everything together:
runtime logging, the Qt event loop, one Controller, and the
Node Picker dialog. All real logic lives in controller.py and
the frontend/backend facades — this file just boots them up.
"""

from __future__ import annotations

import sys

import frontend
import runtime_logger
from controller import Controller
from PySide6.QtWidgets import QApplication


def main() -> None:
    """Start a single SpaceZilla instance.

    Startup order:
        1. Set up logging so every module can use get_logger().
        2. Create the Qt application (required before any widget).
        3. Create a Controller (manages backend + frontend lifecycle).
        4. Show the Node Picker so the user can select or create a node.
           When they do, ctrl.boot() is called with the chosen node_id.
        5. Run the Qt event loop (blocks until all windows close).
        6. Shut down the controller (stops Docker containers, etc.).
    """
    runtime_logger.setup_logging()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    ctrl = Controller()

    # The Node Picker is the first window the user sees.
    # Both callbacks point to ctrl.boot because selecting an existing
    # node and creating a new one follow the same boot path.
    # show_node_picker blocks (dialog.exec) until the user picks a
    # node or closes the dialog.
    frontend.show_node_picker(on_select=ctrl.boot, on_create=ctrl.boot)

    # Only enter the Qt event loop if a node was actually booted
    # (meaning a main window is now open). If the user dismissed the
    # Node Picker without selecting anything, just exit cleanly.
    if ctrl._node_id is not None:
        app.exec()  # blocks until the user closes the app

    ctrl.shutdown()


if __name__ == "__main__":
    main()
