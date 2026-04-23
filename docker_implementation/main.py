"""Entry point for SpaceZilla.

Thin launcher. Wires together runtime logging, the Qt event loop, one
:class:`ZmqController` (container-native pyion backend + ZMQ IPC), and
the Node Picker dialog. All real logic lives in ``backend/`` and
``frontend/`` facades — this file just boots them up.
"""

from __future__ import annotations

import sys

import frontend
import runtime_logger
from backend.zmq_controller import ZmqController
from PySide6.QtWidgets import QApplication


def main() -> None:
    """Start a single SpaceZilla instance.

    Startup order:
        1. Set up logging so every module can use get_logger().
        2. Create the Qt application (required before any widget).
        3. Create a ZmqController (manages Docker + ZMQ IPC lifecycle).
        4. Show the Node Picker so the user can select or create a node.
           Both callbacks point to ctrl.boot — existing nodes and
           newly-created nodes follow the same boot path.
        5. If boot succeeded, open the ver1 main window on the main
           thread and enter the Qt event loop.
        6. On window close, shut the controller down (stops containers,
           closes the IPC client).
    """
    runtime_logger.setup_logging()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    ctrl = ZmqController()

    # Node Picker is the first window the user sees. show_node_picker
    # blocks (dialog.exec) until the user picks a node or closes it.
    frontend.show_node_picker(on_select=ctrl.boot, on_create=ctrl.boot)

    if ctrl.node_id is not None and ctrl.client is not None:
        frontend.show_main_window_ver1(ctrl.client, ctrl.node_id)
        app.exec()

    ctrl.shutdown()


if __name__ == "__main__":
    main()
