"""frontend — GUI layer for SpaceZilla.

The controller calls these functions to show/hide the Node Picker
and main window. All Qt widget creation lives behind this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


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
    raise NotImplementedError


def show_main_window(node_id: str, ipc_port: int) -> None:
    """Switch from the Node Picker to the main SpaceZilla window.

    Args:
        node_id: Which node we're running.
        ipc_port: Port the IPC server is listening on.
    """
    raise NotImplementedError


def teardown() -> None:
    """Close all windows and release Qt resources."""
    raise NotImplementedError
