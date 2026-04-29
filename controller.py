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

import uuid

import backend
import frontend
import store
import uvicorn
from fastapi import FastAPI
from runtime_logger import get_logger
from store.models import Contact, NodeState
from backend.backend_facade import BackendFacade
from backend.rc_generator import generate_contact_plan
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

# Set by Controller.boot() so IPC endpoints can resolve the current node.
_current_node_id: str | None = None

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
def suspend(body: dict) -> dict:
    ok, msg = facade.suspend(body.get("queue_id"))
    return {"ok": ok, "msg": msg}

@ipc_app.post("/queue/cancel")
def cancel(body: dict) -> dict:
    ok, msg = facade.cancel(body.get("queue_id"))
    return {"ok": ok, "msg": msg}

@ipc_app.post("/queue/resume")
def resume(body: dict) -> dict:
    ok, msg = facade.resume(body.get("queue_id"))
    return {"ok": ok, "msg": msg}

@ipc_app.get("/queue")
def get_queue() -> dict:
    return {"queue": facade.get_queue()}

@ipc_app.get("/connected")
def connected() -> dict:
    return {"connected": facade.is_connected()}


@ipc_app.get("/contacts")
def get_contacts() -> dict:
    if _current_node_id is None:
        return {"contacts": []}
    contacts = store.load_contacts(_current_node_id)
    from dataclasses import asdict
    return {"contacts": [asdict(c) for c in contacts]}


@ipc_app.post("/contacts")
def add_contact(body: dict) -> dict:
    if _current_node_id is None:
        return {"ok": False, "msg": "No active node."}
    contact = Contact(
        id=uuid.uuid4().hex,
        name=body["name"],
        peer_entity_num=int(body["peer_entity_num"]),
        peer_host=body["peer_host"],
        peer_port=int(body.get("peer_port", 1114)),
        remote_dest_dir=body.get("remote_dest_dir", "/tmp"),
    )
    store.create_contact(_current_node_id, contact)
    from dataclasses import asdict
    return {"ok": True, "contact": asdict(contact)}


@ipc_app.delete("/contacts/{contact_id}")
def remove_contact(contact_id: str) -> dict:
    if _current_node_id is None:
        return {"ok": False, "msg": "No active node."}
    removed = store.delete_contact(_current_node_id, contact_id)
    return {"ok": removed}


@ipc_app.post("/contacts/{contact_id}/apply")
def apply_contact(contact_id: str) -> dict:
    if _current_node_id is None:
        return {"ok": False, "msg": "No active node."}
    contacts = store.load_contacts(_current_node_id)
    contact = next((c for c in contacts if c.id == contact_id), None)
    if contact is None:
        return {"ok": False, "msg": f"Contact {contact_id} not found."}
    config = store.load_config(_current_node_id)
    rc_text = generate_contact_plan(config, contact)
    logger.info("Applying contact plan for %s (entity %s)", contact.name, contact.peer_entity_num)
    ok, msg = facade.apply_contact_plan(rc_text)
    logger.info("apply_contact_plan: ok=%s msg=%s", ok, msg)
    if not ok:
        return {"ok": False, "msg": msg}
    ok2, msg2 = facade.connect_cfdp(contact.peer_entity_num)
    logger.info("connect_cfdp: ok=%s msg=%s", ok2, msg2)
    return {"ok": ok2, "msg": msg2}
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
            global _current_node_id
            _current_node_id = node_id
            self._node_id = node_id
            self._config = store.load_config(node_id)

            # Build the Docker image if it doesn't exist yet
            backend.build_image()

            self._container_id, container_port = backend.start_container(self._config)
            logger.info("Container started: %s (ion_server port %s)", self._container_id, container_port)

            ok, msg = facade.connect(
                node_number=self._config.ion_node_number,
                entity_id=self._config.ion_entity_id,
                bp_endpoint=self._config.bp_endpoint,
                container_port=container_port,
            )
            logger.info("Backend connect: ok=%s msg=%s", ok, msg)

            self._ensure_initial_contact(node_id, self._config)

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

    def _ensure_initial_contact(self, node_id: str, config) -> None:
        """Add the boot-time receiver as the first contact if not already saved."""
        fields = {f.name: f.value for f in config.rc_fields}
        peer_address = str(fields.get("peer_address", "")).strip()
        if not peer_address:
            return
        try:
            host, port_str = peer_address.rsplit(":", 1)
            port = int(port_str)
        except ValueError:
            return

        existing = store.load_contacts(node_id)
        if any(c.peer_entity_num == config.ion_entity_id for c in existing):
            return  # already saved from a previous boot

        contact = Contact(
            id=uuid.uuid4().hex,
            name=f"Receiver ({host})",
            peer_entity_num=config.ion_entity_id,
            peer_host=host,
            peer_port=port,
        )
        store.create_contact(node_id, contact)
        logger.info("Auto-created initial contact: %s (entity %s)", contact.name, contact.peer_entity_num)

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
