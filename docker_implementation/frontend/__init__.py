"""frontend — GUI layer for SpaceZilla.

The controller calls these functions to show/hide the Node Picker
and main window. All Qt widget creation lives behind this module.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from backend.ipc.client import IpcClient

# We track open windows here so teardown() can close them all
_windows: list = []


def show_node_picker(
    *,
    on_select: Callable[[str], None],
    on_create: Callable[[str], None],
) -> None:
    """Show the Node Picker dialog.

    Args:
        on_select: Called with node_id when the user picks an existing node.
        on_create: Called with node_id when the user creates a new node.
    """
    from frontend.node_picker import open_node_picker

    open_node_picker(on_select=on_select, on_create=on_create)


# DEPRECATED: targets the legacy ver0 HTTP-IPC UI. New code should call
# :func:`show_main_window_ver1`, which loads the ZMQ-backed ver1 window.
def show_main_window(node_id: str, ipc_port: int) -> None:
    """Switch from the Node Picker to the main SpaceZilla window.

    Args:
        node_id: Which node we're running.
        ipc_port: Port the IPC server is listening on.
    """
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    # MainWindow loads .ui files with bare filenames (relative to cwd).
    # We chdir to SpaceZilla_ver0/ so the files are found, then restore.
    sz_dir = str(Path(__file__).parent / "SpaceZilla_ver0")
    original_cwd = os.getcwd()
    os.chdir(sz_dir)
    try:
        sys.path.insert(0, sz_dir)
        from frontend.SpaceZilla_ver0.spacezilla_main import MainWindow

        QApplication.instance() or QApplication(sys.argv)
        window = MainWindow()
    finally:
        os.chdir(original_cwd)

    window.node_id = node_id
    window.ipc_port = ipc_port
    window.show()
    _windows.append(window)


def show_main_window_ver1(client: IpcClient, node_id: str) -> object:
    """Load the ver1 main window, wire it to ``client``, and show it.

    Thin wrapper over :func:`frontend.main_window_ver1.show_main_window_ver1`
    that registers the window in the module-level ``_windows`` list so
    :func:`teardown` still closes everything on shutdown.
    """
    from frontend.main_window_ver1 import show_main_window_ver1 as _show

    return _show(client, node_id, windows=_windows)


def teardown() -> None:
    """Close all windows and release Qt resources.

    The list stores ver0 ``QMainWindow`` instances (which have ``.close()``)
    and ver1 Python wrappers (where the Qt widget lives under
    ``.window``). Handle both shapes transparently.
    """
    for window in _windows:
        closer = getattr(window, "close", None)
        if callable(closer):
            closer()
            continue
        inner = getattr(window, "window", None)
        if inner is not None and hasattr(inner, "close"):
            inner.close()
    _windows.clear()
