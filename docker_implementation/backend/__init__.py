"""backend — Docker lifecycle + container IPC for SpaceZilla nodes.

Re-exports the public functions callers reach for via ``import backend``.
Concrete implementations live in :mod:`backend.docker_backend` and
:mod:`backend.zmq_controller`; the in-container agent and transfer
pipeline live in :mod:`backend.container_agent` and
:mod:`backend.backend_facade`.
"""

from backend.docker_backend import (
    RunningContainer,
    build_image,
    check_docker,
    container_running,
    start_container,
    start_container_legacy,
    start_docker,
    stop_container,
)

__all__ = [
    "RunningContainer",
    "build_image",
    "check_docker",
    "container_running",
    "start_container",
    "start_container_legacy",
    "start_docker",
    "stop_container",
]
