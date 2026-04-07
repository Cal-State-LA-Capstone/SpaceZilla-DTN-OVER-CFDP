"""Node Picker dialog — first window the user sees.

Lists existing nodes, allows creating new ones, and checks
Docker availability before enabling boot actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from store.models import DockerStatus, NodeMeta

if TYPE_CHECKING:
    from collections.abc import Callable


def check_docker_available() -> DockerStatus:
    """Verify Docker is installed, daemon is running, and accessible.

    TODO(teammate): implement real checks. Currently returns OK.
    """
    return DockerStatus.ok()


def load_node_list() -> list[NodeMeta]:
    """Fetch all nodes from the store for display in the picker."""
    raise NotImplementedError


def open_node_picker(
    *,
    on_select: Callable[[str], None],
    on_create: Callable[[str], None],
) -> None:
    """Create and show the NodePickerDialog.

    Loads NodePickerDialog.ui, populates the node list,
    runs the Docker health check, and wires button signals.

    Args:
        on_select: Called with node_id when user selects a node.
        on_create: Called with node_id when user creates a node.
    """
    raise NotImplementedError
