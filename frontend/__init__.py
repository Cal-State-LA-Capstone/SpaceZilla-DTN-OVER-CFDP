"""frontend — GUI layer for SpaceZilla.

The controller calls these functions to show/hide the Node Picker
and main window. All Qt widget creation lives behind this module.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# We track open windows here so teardown() can close them all
_windows: list = []


def show_node_picker(
    *,
    on_select: Callable[[str], None],
    on_create: Callable[[str], None],
) -> None:
    """Show the Node Picker dialog."""
    from frontend.node_picker import open_node_picker

    open_node_picker(on_select=on_select, on_create=on_create)


def show_main_window(node_id: str, ipc_port: int, node_config) -> None:
    """Switch from the Node Picker to the main SpaceZilla window.

    Args:
        node_id: Which node we're running.
        ipc_port: Port the IPC server is listening on.
        node_config: Loaded NodeConfig (ADDED)
    """
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    # Load UI from SpaceZilla_ver1 folder
    sz_dir = str(Path(__file__).parent / "SpaceZilla_ver1")
    original_cwd = os.getcwd()
    os.chdir(sz_dir)

    try:
        sys.path.insert(0, sz_dir)
        from frontend.SpaceZilla_ver1.spacezilla_main import MainWindow

        QApplication.instance() or QApplication(sys.argv)

        window = MainWindow()

        # ============================
        # CHANGED: initialize contacts properly
        # ============================
        # WHY:
        # Contacts now require datastore + config to function.
        # This ensures UI loads real contacts and can apply contact plans.
        window.init_contacts(node_id, node_config)

    finally:
        os.chdir(original_cwd)

    window.node_id = node_id
    window.ipc_port = ipc_port

    window.show()
    _windows.append(window)


def teardown() -> None:
    """Close all windows and release Qt resources."""
    for window in _windows:
        try:
            # CHANGED: support wrapper objects
            if hasattr(window, "close") and callable(window.close):
                window.close()
            elif hasattr(window, "window") and hasattr(window.window, "close"):
                window.window.close()
        except Exception:
            pass

    _windows.clear()