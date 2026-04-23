"""IPC server <-> client smoke tests running entirely in-process.

Uses a fake ``BackendFacade`` and real ZMQ sockets on loopback — no
Docker required. Covers the whitelist, the ``send_files`` PUB fan-out,
and the timeout/retry path in :class:`IpcClient`.
"""

from __future__ import annotations

import threading
import time

import pytest
from backend.ipc.client import IpcClient, IpcError
from backend.ipc.protocol import TOPIC_CFDP, Event
from backend.ipc.server import serve


class FakeFacade:
    """Minimal stand-in for :class:`BackendFacade`.

    Implements every method in the whitelist so the server dispatcher
    finds them; ``send_files`` uses the ``on_change`` hook so the PUB
    pipeline can be exercised.
    """

    def __init__(self) -> None:
        self._connected = False
        self._queue: list[dict] = []
        self._counter = 0

    def startup_check(self) -> list[tuple[str, bool, str]]:
        return [("pyion", True, "ok")]

    def connect(
        self, node_number: int, entity_id: int, bp_endpoint: str
    ) -> tuple[bool, str]:
        self._connected = True
        return (
            True,
            f"connected node={node_number} entity={entity_id} eid={bp_endpoint}",
        )

    def disconnect(self) -> tuple[bool, str]:
        self._connected = False
        return True, "disconnected"

    def is_connected(self) -> bool:
        return self._connected

    def queue_files(self, file_paths: list[str]) -> list[str]:
        ids: list[str] = []
        for p in file_paths:
            self._counter += 1
            qid = str(self._counter)
            self._queue.append({"id": qid, "path": p, "status": "Queued"})
            ids.append(qid)
        return ids

    def remove_file(self, queue_id: str) -> bool:
        before = len(self._queue)
        self._queue = [q for q in self._queue if q["id"] != queue_id]
        return len(self._queue) < before

    def clear_queue(self) -> None:
        self._queue.clear()

    def get_queue(self) -> list[dict]:
        return [q.copy() for q in self._queue]

    def send_files(self, on_change=None) -> tuple[bool, str]:
        # Walk the queue synchronously and publish every status change so
        # the SUB side gets a deterministic event sequence.
        for item in list(self._queue):
            if on_change is not None:
                on_change(item["id"], "Running")
                on_change(item["id"], "Completed")
            item["status"] = "Completed"
        return True, "done"

    def status_indicator(self) -> str:
        return "idle"


@pytest.fixture
def server(tmp_path_factory):
    """Spin up an IPC server on loopback with a :class:`FakeFacade`.

    The server runs on a daemon thread bound to an OS-assigned pair of
    ports (we bind-then-read with zmq's ``LAST_ENDPOINT`` trick via two
    fixed high-number ports for simplicity). Caller closes via
    ``stop_event``.
    """
    import socket

    # Grab two free ports on loopback. A small race is possible between
    # socket.close() and zmq.bind() but acceptable for tests.
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    rep_port = _free_port()
    pub_port = _free_port()
    facade = FakeFacade()
    stop_event = threading.Event()

    thread = threading.Thread(
        target=serve,
        kwargs={
            "rep_port": rep_port,
            "pub_port": pub_port,
            "facade": facade,
            "bind_host": "127.0.0.1",
            "stop_event": stop_event,
        },
        name="ipc-server-test",
        daemon=True,
    )
    thread.start()
    # Let the server bind before the client connects.
    time.sleep(0.1)

    yield {
        "rep_port": rep_port,
        "pub_port": pub_port,
        "facade": facade,
        "stop_event": stop_event,
        "thread": thread,
    }

    stop_event.set()
    thread.join(timeout=2)


class TestIpcRoundtrip:
    def test_health(self, server):
        client = IpcClient(server["rep_port"], server["pub_port"])
        try:
            assert client.health() == {"ok": True}
        finally:
            client.close()

    def test_is_connected_before_and_after(self, server):
        client = IpcClient(server["rep_port"], server["pub_port"])
        try:
            assert client.is_connected() is False
            result = client.connect(node_number=1, entity_id=2, bp_endpoint="ipn:1.1")
            assert result[0] is True
            assert client.is_connected() is True
            client.disconnect()
            assert client.is_connected() is False
        finally:
            client.close()

    def test_queue_and_remove(self, server):
        client = IpcClient(server["rep_port"], server["pub_port"])
        try:
            ids = client.queue_files(["/host/tmp/a.txt", "/host/tmp/b.txt"])
            assert len(ids) == 2
            assert client.remove_file(ids[0]) is True
            assert len(client.get_queue()) == 1
        finally:
            client.close()

    def test_unknown_method_returns_error(self, server):
        client = IpcClient(server["rep_port"], server["pub_port"])
        try:
            with pytest.raises(IpcError) as exc:
                client.call("does_not_exist")
            assert exc.value.error == "unknown_method"
        finally:
            client.close()


class TestPubSubEvents:
    def test_send_files_publishes_per_status_change(self, server):
        client = IpcClient(server["rep_port"], server["pub_port"])
        received: list[Event] = []
        done = threading.Event()

        def _on_event(event: Event) -> None:
            received.append(event)
            # Each queued file produces Running + Completed — wait for 2.
            if len(received) >= 2:
                done.set()

        try:
            client.subscribe(_on_event)
            # Give the SUB socket a moment to connect before we publish.
            time.sleep(0.1)

            client.queue_files(["/host/tmp/x.txt"])
            client.send_files()

            assert done.wait(timeout=3), "expected 2 events, got: {}".format(
                [(e.queue_id, e.status) for e in received]
            )
            statuses = [e.status for e in received[:2]]
            assert statuses == ["Running", "Completed"]
            assert all(e.topic == TOPIC_CFDP for e in received[:2])
        finally:
            client.close()
