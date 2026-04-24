"""Entry point for SpaceZilla."""

from __future__ import annotations

import sys
import time

import frontend
import runtime_logger
from controller import Controller
from PySide6.QtWidgets import QApplication

logger = runtime_logger.get_logger("main")


def main() -> None:
    runtime_logger.setup_logging()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    ctrl = Controller()

    # Node picker
    frontend.show_node_picker(on_select=ctrl.boot, on_create=ctrl.boot)

    # ============================
    # CHANGED: pass config into UI
    # ============================
    if ctrl._node_id is not None and ctrl._ipc_port is not None:
        for attempt in range(5):
            ok, msg = ctrl.connect()
            if ok:
                logger.info("Backend connected")
                break
            logger.warning("Connect attempt %d/5 failed: %s", attempt + 1, msg)
            time.sleep(1)
        else:
            logger.error("Backend failed to connect after 5 attempts")

        # CHANGED: added ctrl._config
        frontend.show_main_window(
            ctrl._node_id,
            ctrl._ipc_port,
        )

        app.exec()

    ctrl.shutdown()


if __name__ == "__main__":
    main()