"""frontend — GUI facade for the SpaceZilla controller.

Provides high-level functions the controller uses to display
the Node Picker, boot the main window, and tear down the GUI.
All Qt object creation happens behind this facade.
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
    """Display the Node Picker dialog.

    Args:
        on_select: Called with ``node_id`` when the user picks
            an existing node.
        on_create: Called with ``node_id`` when the user creates
            a new node via the form.
    """
    raise NotImplementedError


def show_main_window(node_id: str, ipc_port: int) -> None:
    """Switch from the Node Picker to the main SpaceZilla window.

    Args:
        node_id: The active node's identifier.
        ipc_port: The IPC server port for backend communication.
    """
    raise NotImplementedError


def teardown() -> None:
    """Close all windows and release Qt resources."""
    raise NotImplementedError
