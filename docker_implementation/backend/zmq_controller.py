"""Host-side lifecycle manager for a single SpaceZilla node.

Replaces the FastAPI/uvicorn-based :mod:`controller` for the new
container-native pyion architecture. Boot order:

    1. load the node's config from :mod:`store`.
    2. build the Docker image (no-op if already present).
    3. read the host-mount consent setting.
    4. run ``docker run`` with dynamic ports + (optional) bind mount.
    5. spin up an :class:`IpcClient` against the published ports.
    6. poll ``client.health()`` until the in-container agent is ready.
    7. write a ``state.json`` with ``status="running"``.

Shutdown reverses the sequence and is safe to call after a failed boot.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from runtime_logger import get_logger
from store import (
    GlobalSettings,
    NodeState,
    load_config,
    load_settings,
    save_state,
)

from backend.backend_facade import (
    BackendFacade,  # noqa: F401  (type-only hint for serve)
)
from backend.docker_backend import (
    build_image,
    start_container,
    stop_container,
)
from backend.ipc.client import IpcClient, IpcError

if TYPE_CHECKING:
    from store import NodeConfig

    from backend.docker_backend import RunningContainer

logger = get_logger("zmq_controller")

# How long to wait for the in-container agent to respond to health().
# pyion + ionstart take ~5 s on a warm host; 20 s leaves margin.
_HEALTH_TIMEOUT_S: float = 20.0
_HEALTH_POLL_S: float = 1.0


class ZmqController:
    """Boot-to-shutdown manager for exactly one node.

    Usage::

        ctrl = ZmqController()
        if ctrl.boot(node_id):
            # ctrl.client is the IpcClient the GUI should talk to
            ...
        ctrl.shutdown()
    """

    def __init__(self) -> None:
        self._node_id: str | None = None
        self._config: NodeConfig | None = None
        self._running: RunningContainer | None = None
        self._client: IpcClient | None = None
        logger.info("ZmqController created (pre-boot)")

    # -- Public API -------------------------------------------------------

    @property
    def node_id(self) -> str | None:
        return self._node_id

    @property
    def client(self) -> IpcClient | None:
        return self._client

    @property
    def ipc_port(self) -> int | None:
        return self._running.rep_port if self._running else None

    def boot(self, node_id: str) -> bool:
        """Bring up the container + IPC for ``node_id``.

        Returns True on success. On failure, :meth:`shutdown` is invoked
        internally so there are no leaked resources.
        """
        logger.info("Booting node %s", node_id)
        self._node_id = node_id

        try:
            self._config = load_config(node_id)

            build_image()

            settings: GlobalSettings = load_settings()
            host_mount = bool(settings.host_mount_consent)

            self._running = start_container(self._config, host_mount=host_mount)
            logger.info(
                "Container started: %s (REP=%d PUB=%d)",
                self._running.container_id,
                self._running.rep_port,
                self._running.pub_port,
            )

            self._client = IpcClient(
                rep_port=self._running.rep_port,
                pub_port=self._running.pub_port,
            )

            if not self._wait_for_health():
                raise RuntimeError(
                    "container agent did not become healthy within timeout"
                )

            save_state(
                node_id,
                NodeState(
                    node_id=node_id,
                    pid=os.getpid(),
                    ipc_port=self._running.rep_port,
                    container_id=self._running.container_id,
                    status="running",
                ),
            )
            return True

        except Exception:
            logger.exception("Boot failed for node %s", node_id)
            self.shutdown()
            return False

    def shutdown(self) -> None:
        """Tear everything down in reverse order.

        Safe to call after a failed boot or without a prior boot.
        """
        logger.info("Shutting down node %s", self._node_id)

        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                logger.exception("IpcClient.close raised")
            self._client = None

        if self._running is not None:
            try:
                stop_container(self._running.container_id)
                logger.info("Container stopped: %s", self._running.container_id)
            except Exception:
                logger.exception("stop_container raised")
            self._running = None

        if self._node_id is not None:
            try:
                save_state(
                    self._node_id,
                    NodeState(node_id=self._node_id, status="stopped"),
                )
            except Exception:
                logger.exception("save_state stopped raised")

    # -- Internal helpers -------------------------------------------------

    def _wait_for_health(self) -> bool:
        assert self._client is not None
        deadline = time.monotonic() + _HEALTH_TIMEOUT_S
        while time.monotonic() < deadline:
            try:
                result = self._client.health()
                if isinstance(result, dict) and result.get("ok"):
                    logger.info("container agent healthy")
                    return True
            except IpcError as exc:
                logger.debug("health not ready: %s", exc.error)
            time.sleep(_HEALTH_POLL_S)
        return False
