"""Central orchestrator for a single SpaceZilla node.

Each running SpaceZilla process creates exactly one Controller.
The Controller handles the full lifecycle of a node:

    1. Load the node's saved config from disk  (store)
    2. Start the local ION node process        (backend)
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
from backend.facade import BackendFacade
from fastapi import FastAPI
from runtime_logger import get_logger
from store.models import NodeState
import uuid
from store.models import Contact

if TYPE_CHECKING:
    from store.models import NodeConfig

logger = get_logger("controller")

# -- Facade ------------------------------------------------------------------
# One instance shared across all IPC routes.
_facade = BackendFacade()

# -- IPC FastAPI app ---------------------------------------------------------

ipc_app = FastAPI()


@ipc_app.get("/health")
def health() -> dict[str, str]:
    """Simple health-check so other parts of the system can verify
    this node's IPC server is alive."""
    return {"status": "ok"}


@ipc_app.post("/connect")
def connect(node_number: int, entity_id: int, bp_endpoint: str) -> dict:
    ok, msg = _facade.connect(
        node_number=node_number,
        entity_id=entity_id,
        bp_endpoint=bp_endpoint,
    )
    return {"ok": ok, "message": msg}


@ipc_app.post("/disconnect")
def disconnect() -> dict:
    ok, msg = _facade.disconnect()
    return {"ok": ok, "message": msg}


@ipc_app.get("/is_connected")
def is_connected() -> dict:
    return {"connected": _facade.is_connected()}


@ipc_app.post("/queue")
def queue_files(file_paths: list[str]) -> dict:
    print(f"IPC /queue: connected={_facade.is_connected()}, file_paths={file_paths}")
    ids = _facade.queue_files(file_paths)
    print(f"IPC /queue result: ids={ids}")
    return {"queue_ids": ids}


@ipc_app.delete("/queue/{queue_id}")
def remove_file(queue_id: str) -> dict:
    ok = _facade.remove_file(queue_id)
    return {"ok": ok}


@ipc_app.delete("/queue")
def clear_queue() -> dict:
    _facade.clear_queue()
    return {"ok": True}


@ipc_app.get("/queue")
def get_queue() -> dict:
    return {"queue": _facade.get_queue()}


@ipc_app.post("/send")
def send_files() -> dict:
    print(f"IPC /send: connected={_facade.is_connected()}")
    ok, msg = _facade.send_files()
    print(f"IPC /send result: ok={ok}, msg={msg}")
    return {"ok": ok, "message": msg}


@ipc_app.post("/suspend")
def suspend() -> dict:
    ok, msg = _facade.suspend()
    return {"ok": ok, "message": msg}


@ipc_app.post("/cancel")
def cancel() -> dict:
    ok, msg = _facade.cancel()
    return {"ok": ok, "message": msg}


@ipc_app.post("/resume")
def resume() -> dict:
    ok, msg = _facade.resume()
    return {"ok": ok, "message": msg}


@ipc_app.get("/status")
def status() -> dict:
    return {"status": _facade.status_indicator()}


@ipc_app.post("/contact_plan")
def contact_plan(peer_host: str, peer_num: int, peer_port: int = 4556) -> dict:
    """Apply a contact plan to link this node to a peer."""
    if _controller is None or _controller._config is None:
        return {"ok": False, "message": "controller not ready"}
    try:
        backend.apply_contact_plan(_controller._config, peer_host, peer_num, peer_port)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "message": str(e)}
    
@ipc_app.get("/contacts")
def get_contacts() -> dict:
    if _controller is None or _controller._node_id is None:
        return {"contacts": []}

    contacts = store.load_contacts(_controller._node_id)
    return {"contacts": [c.__dict__ for c in contacts]}


@ipc_app.post("/contacts")
def add_contact(
    name: str,
    peer_entity_num: int,
    peer_host: str,
    peer_port: int = 4556,
    remote_dest_dir: str = "/tmp",
) -> dict:
    if _controller is None or _controller._node_id is None:
        return {"ok": False, "message": "controller not ready"}

    contacts = store.load_contacts(_controller._node_id)

    contact = Contact(
        id=uuid.uuid4().hex,
        name=name,
        peer_entity_num=peer_entity_num,
        peer_host=peer_host,
        peer_port=peer_port,
        remote_dest_dir=remote_dest_dir,
    )

    contacts.append(contact)
    store.save_contacts(_controller._node_id, contacts)

    return {"ok": True, "contact": contact.__dict__}


@ipc_app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: str) -> dict:
    if _controller is None or _controller._node_id is None:
        return {"ok": False, "message": "controller not ready"}

    contacts = store.load_contacts(_controller._node_id)
    new_contacts = [c for c in contacts if c.id != contact_id]

    if len(new_contacts) == len(contacts):
        return {"ok": False, "message": "contact not found"}

    store.save_contacts(_controller._node_id, new_contacts)
    return {"ok": True}


# -- Controller --------------------------------------------------------------


class Controller:
    """Manages the full boot-to-shutdown lifecycle of one node.

    Usage::

        ctrl = Controller()   # nothing running yet ("pre-boot")
        ctrl.boot(node_id)    # loads config, starts ION + IPC
        ctrl.connect()        # connects backend facade (call from main thread)
        ...
        ctrl.shutdown()       # tears everything down
    """

    def __init__(self) -> None:
        self._node_id: str | None = None
        self._config: NodeConfig | None = None
        self._ion_rc: str | None = None
        self._ipc_port: int | None = None
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        logger.info("Controller created (pre-boot)")

    # -- Public API ----------------------------------------------------------

    def boot(self, node_id: str) -> bool:
        """Bring up everything needed to run a node.

        Returns True on success, False if something went wrong.
        On failure any partially-started resources are cleaned up
        automatically via shutdown().

        Steps (in order):
            1. Read the node's config.json from disk.
            2. Start the ION node process directly on the host.
            3. Start the ION log capture thread.
            4. Start a local IPC server so the GUI can talk to the controller.
            5. Write the runtime state (PID, port) to disk.

        Note: connect() must be called separately from the main thread
        after boot() returns, because pyion requires the main thread.
        """
        global _controller
        logger.info("Booting node %s", node_id)

        try:
            self._node_id = node_id
            self._config = store.load_config(node_id)
            _controller = self

            self._ion_rc = backend.start_ion(self._config)
            logger.info("ION node started, rc at %s", self._ion_rc)

            backend.start_ion_logger()

            self._start_ipc_server()

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
                    status="running",
                ),
            )

            return True

        except Exception as e:
            logger.error("Boot failed for node %s: %s", node_id, e)
            self.shutdown()
            return False

    def connect(self) -> tuple[bool, str]:
        """Connect the backend facade to this node's BP endpoint.

        Must be called from the main thread — pyion uses Python signals
        internally which only work on the main thread.
        """

        
        if self._config is None:
            return False, "not booted"
        
        # Hardcoded facade connect
        local_node = self._config.ion_node_number
        peer_entity_id = 2 if local_node == 1 else 1
        bp_endpoint = f"ipn:{local_node}.1"

        print(f"Controller.connect -> node={local_node}, peer_entity={peer_entity_id}, bp_endpoint={bp_endpoint}")
        return _facade.connect(
            node_number=local_node,
            entity_id=peer_entity_id,
            bp_endpoint=bp_endpoint,
        )
    
        '''
        return _facade.connect(
            node_number=self._config.ion_node_number,
            entity_id=self._config.ion_entity_id,
            bp_endpoint=self._config.bp_endpoint,
        )
        '''

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

        if _facade.is_connected():
            _facade.disconnect()
            logger.info("Pyion shut down")

        backend.stop_ion()
        logger.info("ION node stopped")

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

        We bind to 127.0.0.1 (loopback only) with port 0 so the OS
        gives us a free port.
        """
        config = uvicorn.Config(
            app=ipc_app,
            host="127.0.0.1",
            port=0,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)

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


# module-level reference set during boot() so contact_plan route can access config
_controller: Controller | None = None