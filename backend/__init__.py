"""backend — Docker/ION lifecycle facade.

The controller calls these functions to build, start, and stop
Docker containers that run ION nodes. Each container corresponds
to one SpaceZilla node instance.
"""

from __future__ import annotations

from store.models import DockerStatus, NodeConfig


def build_image(*, force: bool = False) -> None:
    """Build the ION Docker image if it does not already exist.

    Args:
        force: Rebuild even if the image is present.
    """
    raise NotImplementedError


def start_container(config: NodeConfig) -> str:
    """Start a Docker container for the given node configuration.

    Returns the Docker container ID.
    """
    raise NotImplementedError


def stop_container(container_id: str) -> None:
    """Stop and remove a running container."""
    raise NotImplementedError


def container_running(container_id: str) -> bool:
    """Check whether the given container is currently running."""
    raise NotImplementedError


def check_docker() -> DockerStatus:
    """Check Docker availability (installed, daemon up, permissions)."""
    raise NotImplementedError
