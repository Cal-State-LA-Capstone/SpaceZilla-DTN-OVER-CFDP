"""Central orchestrator for a single SpaceZilla node.

Each running SpaceZilla process creates exactly one Controller.
The Controller handles the full lifecycle of a node:

    1. Load the node's saved config from disk  (store)
    2. Spin up its Docker container            (backend)
    3. Start a local HTTP server for IPC       (FastAPI / uvicorn)
    4. Open the GUI main window                (frontend)
    5. On exit, tear everything down in reverse
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING

import backend
import frontend
import store
import uvicorn
from fastapi import FastAPI
from runtime_logger import get_logger
from store.models import NodeState
from backend.backend_facade import BackendFacade
from runtime_logger import ionlog_parser

if TYPE_CHECKING:
    from store.models import NodeConfig

logger = get_logger("controller")

# -- IPC FastAPI app ---------------------------------------------------------
# Lives at module level because uvicorn needs a importable app object.
# Right now it only has a health-check endpoint; more routes will be
# added here as features are built out.

ipc_app = FastAPI()

facade = BackendFacade()

@ipc_app.get("/health")
def health() -> dict[str, str]:
    """Simple health-check so other parts of the system can verify
    this node's IPC server is alive."""
    return {"status": "ok"}

@ipc_app.post("/queue/enqueue")
def enqueue(body:dict) -> dict:
    ids = facade.queue_files(body["paths"])
    return {"ids": ids}

@ipc_app.post("/queue/send")
def send() -> dict:
    ok, msg = facade.send_files()
    return {"ok":ok, "msg":msg}

@ipc_app.post("/queue/suspend")
def suspend() -> dict:
    ok, msg = facade.suspend()
    return {"ok": ok, "msg":msg}

@ipc_app.post("/queue/cancel")
def cancel() -> dict:
    ok, msg = facade.cancel()
    return {"ok":ok, "msg":msg}

@ipc_app.post("/queue/resume")
def resume() -> dict:
    ok, msg = facade.resume()
    return {"ok":ok, "msg":msg}

@ipc_app.get("/queue")
def get_queue() -> dict:
    return {"queue": facade.get_queue()}
# -- Controller --------------------------------------------------------------


class Controller:
    """Manages the full boot-to-shutdown lifecycle of one node.

    Usage::

        ctrl = Controller()   # nothing running yet ("pre-boot")
        ctrl.boot(node_id)    # loads config, starts container + IPC + GUI
        ...
        ctrl.shutdown()       # tears everything down
    """

    def __init__(self) -> None:
        # All of these start as None and get filled in during boot().
        self._node_id: str | None = None
        self._config: NodeConfig | None = None
        self._container_id: str | None = None
        self._ipc_port: int | None = None
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        logger.info("Controller created (pre-boot)")

    # -- Public API ----------------------------------------------------------

    def boot(self, node_id: str) -> bool:
        """Bring up everything needed to run a node.

        Returns True on success, False if something went wrong.
        On failure any partially-started resources (container, IPC
        server) are cleaned up automatically via shutdown().

        Steps (in order):
            1. Read the node's config.json from disk.
            2. Ask the backend to start a Docker container for this node.
            3. Start a local IPC server so the GUI (and tests) can talk
               to the controller over HTTP.
            4. Write the runtime state (PID, port, container ID) to disk
               so other processes can discover this node.
            5. Tell the frontend to show the main SpaceZilla window.
        """
        logger.info("Booting node %s", node_id)

        self._ion_parser = ionlog_parser()
        self._ion_parser.start()

        try:
            self._node_id = node_id
            self._config = store.load_config(node_id)

            # Build the Docker image if it doesn't exist yet
            backend.build_image()

            self._container_id = backend.start_container(self._config)
            logger.info("Container started: %s", self._container_id)
            
            ok, msg = facade.connect(
                node_number=self._config.ion_node_number,
                entity_id=self._config.ion_entity_id,
                bp_endpoint=self._config.bp_endpoint,
                )
            logger.info("Backend connect: ok=%s msg=%s", ok, msg)

            # logger.info("Capturing ion.log")
            # backend.start_ion_logger(self._container_id)  # not yet implemented
            self._start_ipc_server()

            # Uvicorn binds the socket in its thread — wait for the port
            for _ in range(50):
                if self._ipc_port is not None:
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("IPC server did not bind within 5 seconds")

            logger.info("IPC server listening on 127.0.0.1:%s", self._ipc_port)

            store.save_state(
                node_id,
                NodeState(
                    node_id=node_id,
                    pid=os.getpid(),
                    ipc_port=self._ipc_port,
                    container_id=self._container_id,
                    status="running",
                ),
            )

            # GUI window is created by main.py on the main thread
            # (Qt widgets can't be created from a worker thread).
            return True

        except Exception as e:
            logger.error("Boot failed for node %s: %s", node_id, e)
            self.shutdown()
            return False

    def spawn_peer(self) -> None:
        """Open a brand-new SpaceZilla process for a second node.

        This is fire-and-forget -- we don't track the child PID.
        The new process will show its own Node Picker dialog.
        """
        subprocess.Popen([sys.executable, "-m", "spacezilla"])  # noqa: S603
        logger.info("Spawned peer process")

    def shutdown(self) -> None:
        """Tear everything down in reverse order.

        Safe to call even if boot() was never called or only partially
        completed -- each step checks whether there's anything to clean up.
        """
        logger.info("Shutting down node %s", self._node_id)

        self._stop_ipc_server()
        self._ion_parser.stop()

        #self._ion_parser = ionlog_parser()
        #self._ion_parser.start()
        #facade.set_parser(self._ion_parser)

        if self._container_id is not None:
            backend.stop_container(self._container_id)
            logger.info("Container stopped: %s", self._container_id)

        facade.disconnect()

        # Mark the node as stopped on disk so the Node Picker shows the
        # correct status next time it's opened.
        if self._node_id is not None:
            store.save_state(
                self._node_id,
                NodeState(node_id=self._node_id, status="stopped"),
            )

        frontend.teardown()
        logger.info("Shutdown complete")

    # -- IPC server helpers --------------------------------------------------

    def _start_ipc_server(self) -> None:
        """Start the FastAPI IPC server in a background thread.

        We bind to 127.0.0.1 (loopback only, never exposed to the
        network) with port 0 so the OS gives us a free port.

        The tricky part: uvicorn doesn't tell us which port the OS
        picked until *after* the server sockets are bound.  So we
        monkey-patch the startup coroutine to grab the port from the
        live socket once it's ready.
        """
        config = uvicorn.Config(
            app=ipc_app,
            host="127.0.0.1",
            port=0,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)

        # -- Monkey-patch to discover the ephemeral port ----------------
        # After uvicorn binds its sockets we inspect them to find out
        # which port the OS assigned, then store it in self._ipc_port.
        original_startup = self._server.startup

        async def _patched_startup(
            sockets: list | None = None,  # type: ignore[type-arg]
        ) -> None:
            await original_startup(sockets=sockets)
            if self._server and self._server.servers:
                for server in self._server.servers:
                    for sock in server.sockets:
                        addr = sock.getsockname()
                        self._ipc_port = addr[1]
                        return

        self._server.startup = _patched_startup  # type: ignore[assignment]

        # daemon=True so the thread dies automatically if the main
        # process exits unexpectedly (no zombie threads).
        self._server_thread = threading.Thread(
            target=self._server.run,
            daemon=True,
        )
        self._server_thread.start()

    def _stop_ipc_server(self) -> None:
        """Ask uvicorn to stop and wait for its thread to finish."""
        if self._server is not None:
            self._server.should_exit = True
        if self._server_thread is not None:
            self._server_thread.join(timeout=5)
            self._server_thread = None
        self._server = None
