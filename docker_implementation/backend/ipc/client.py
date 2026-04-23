"""Host-side ZMQ IPC client.

Used by :mod:`backend.zmq_controller` and the ver1 main window. Wraps a
REQ socket for commands (:meth:`call`) and spins a daemon thread on a SUB
socket for transfer events (:meth:`subscribe`). GUI callers must marshal
callback work onto the Qt event loop themselves — the subscribe thread
fires on a worker thread.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from typing import Any

import zmq
from runtime_logger import get_logger

from backend.ipc.protocol import TOPIC_CFDP, Event, Reply, Request

logger = get_logger("ipc.client")

# Per-call REQ timeout (ms). Short on purpose — any real work runs in a
# container-side thread and is reported back via PUB events, so a REP
# call that blocks for >5 s indicates the agent is stuck.
_RECV_TIMEOUT_MS: int = 5000


class IpcError(RuntimeError):
    """Raised when the container agent reports a non-ok reply."""

    def __init__(self, method: str, error: str) -> None:
        super().__init__(f"{method}: {error}")
        self.method = method
        self.error = error


class IpcClient:
    """Connects to the container agent's REP/PUB pair.

    ``host`` should stay ``127.0.0.1`` — ports are published by
    :func:`backend.docker_backend.start_container` after ``docker port``
    resolves the OS-assigned mapping.
    """

    def __init__(self, rep_port: int, pub_port: int, host: str = "127.0.0.1") -> None:
        self._rep_port = rep_port
        self._pub_port = pub_port
        self._host = host
        self._ctx = zmq.Context.instance()
        self._req_lock = threading.Lock()
        self._req = self._make_req()
        self._sub_thread: threading.Thread | None = None
        self._sub_stop = threading.Event()

    # -- REQ side ---------------------------------------------------------

    def _make_req(self) -> zmq.Socket:
        sock = self._ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, _RECV_TIMEOUT_MS)
        sock.setsockopt(zmq.LINGER, 0)
        sock.connect(f"tcp://{self._host}:{self._rep_port}")
        return sock

    def _reset_req(self) -> None:
        """Rebuild the REQ socket after a timeout.

        ZMQ REQ sockets get stuck in the ``recv`` state after a send
        without a reply, so the only safe recovery is to close and
        reconnect.
        """
        try:
            self._req.close(linger=0)
        except Exception:
            pass
        self._req = self._make_req()

    def call(self, method: str, **args: Any) -> Any:
        """Send one request, return the ``result`` field, retry once on timeout."""
        request = Request(id=str(uuid.uuid4()), method=method, args=args)
        raw = request.to_json()

        with self._req_lock:
            for attempt in (1, 2):
                try:
                    self._req.send(raw)
                    reply_bytes = self._req.recv()
                    break
                except zmq.Again:
                    logger.warning("REQ timeout on %s (attempt %d/2)", method, attempt)
                    self._reset_req()
                    if attempt == 2:
                        raise IpcError(method, "timeout") from None
            else:
                raise IpcError(method, "timeout")

        reply = Reply.from_json(reply_bytes)
        if not reply.ok:
            raise IpcError(method, reply.error or "unknown_error")
        return reply.result

    # -- Convenience wrappers mirroring BackendFacade --------------------

    def health(self) -> dict[str, Any]:
        return self.call("health")

    def startup_check(self) -> list[list[Any]]:
        return self.call("startup_check")

    def connect(self, node_number: int, entity_id: int, bp_endpoint: str) -> list[Any]:
        return self.call(
            "connect",
            node_number=node_number,
            entity_id=entity_id,
            bp_endpoint=bp_endpoint,
        )

    def disconnect(self) -> list[Any]:
        return self.call("disconnect")

    def is_connected(self) -> bool:
        return bool(self.call("is_connected"))

    def queue_files(self, file_paths: list[str]) -> list[str]:
        return self.call("queue_files", file_paths=file_paths)

    def remove_file(self, queue_id: str) -> bool:
        return bool(self.call("remove_file", queue_id=queue_id))

    def clear_queue(self) -> None:
        self.call("clear_queue")

    def get_queue(self) -> list[dict[str, Any]]:
        return self.call("get_queue")

    def send_files(self) -> list[Any]:
        return self.call("send_files")

    def status_indicator(self) -> str:
        return str(self.call("status_indicator"))

    # -- PUB/SUB side -----------------------------------------------------

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """Start a daemon thread receiving transfer events.

        ``callback`` runs on the subscriber thread, not the caller's
        thread. Qt code must re-dispatch to the GUI thread via
        ``QMetaObject.invokeMethod(..., Qt.QueuedConnection)``.
        """
        if self._sub_thread and self._sub_thread.is_alive():
            return

        self._sub_stop.clear()

        def _run() -> None:
            sub = self._ctx.socket(zmq.SUB)
            sub.setsockopt(zmq.LINGER, 0)
            sub.connect(f"tcp://{self._host}:{self._pub_port}")
            sub.setsockopt_string(zmq.SUBSCRIBE, TOPIC_CFDP)
            poller = zmq.Poller()
            poller.register(sub, zmq.POLLIN)
            try:
                while not self._sub_stop.is_set():
                    events = dict(poller.poll(timeout=500))
                    if sub in events:
                        frames = sub.recv_multipart()
                        if len(frames) != 2:
                            logger.warning(
                                "subscribe got %d frames, expected 2", len(frames)
                            )
                            continue
                        try:
                            event = Event.from_json(frames[1])
                        except Exception as exc:
                            logger.warning("subscribe bad event: %s", exc)
                            continue
                        try:
                            callback(event)
                        except Exception:
                            logger.exception("subscribe callback raised")
            finally:
                sub.close(linger=0)

        self._sub_thread = threading.Thread(target=_run, name="ipc-sub", daemon=True)
        self._sub_thread.start()

    def close(self) -> None:
        """Stop the SUB thread and close the REQ socket."""
        self._sub_stop.set()
        if self._sub_thread is not None:
            self._sub_thread.join(timeout=2)
            self._sub_thread = None
        try:
            self._req.close(linger=0)
        except Exception:
            pass
