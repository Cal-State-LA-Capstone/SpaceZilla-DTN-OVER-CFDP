"""In-container ZMQ server.

``serve`` binds a REP socket for commands and a PUB socket for transfer
events, then runs a blocking dispatcher loop on the REP socket. Each
command is resolved against a whitelist and called on the supplied
``BackendFacade`` instance. ``send_files`` is special-cased so the
per-transfer ``on_change`` callback publishes a PUB event for every queue
status change.
"""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import zmq
from runtime_logger import get_logger

from backend.ipc.protocol import (
    ERR_BAD_REQUEST,
    ERR_EXCEPTION,
    ERR_UNKNOWN_METHOD,
    METHODS,
    TOPIC_CFDP,
    Event,
    Reply,
    Request,
)

if TYPE_CHECKING:
    from backend.backend_facade import BackendFacade

logger = get_logger("ipc.server")


def _health(_facade: BackendFacade) -> dict[str, bool]:
    """Lightweight liveness probe — used by the host boot loop."""
    return {"ok": True}


def _dispatch(
    facade: BackendFacade,
    request: Request,
    publish: Callable[[Event], None],
) -> Reply:
    """Run a single request against the facade and produce a reply."""
    method_name = request.method

    if method_name == "health":
        return Reply(id=request.id, ok=True, result=_health(facade))

    if method_name not in METHODS:
        return Reply(id=request.id, ok=False, error=ERR_UNKNOWN_METHOD)

    method = getattr(facade, method_name, None)
    if method is None:
        return Reply(id=request.id, ok=False, error=ERR_UNKNOWN_METHOD)

    try:
        if method_name == "send_files":
            # Wire the facade's on_change hook through to the PUB socket so
            # host subscribers see each queue_id -> status transition.
            def on_change(queue_id: str, status: str) -> None:
                publish(
                    Event(topic=TOPIC_CFDP, queue_id=str(queue_id), status=str(status))
                )

            args = dict(request.args or {})
            args["on_change"] = on_change
            result = method(**args)
        else:
            result = method(**(request.args or {}))
    except TypeError as exc:
        # Bad kwargs from the host — surface the message without crashing
        # the serve loop.
        logger.warning("bad_request for method=%s: %s", method_name, exc)
        return Reply(id=request.id, ok=False, error=f"{ERR_BAD_REQUEST}: {exc}")
    except Exception as exc:
        logger.exception("exception in method=%s", method_name)
        return Reply(id=request.id, ok=False, error=f"{ERR_EXCEPTION}: {exc}")

    return Reply(id=request.id, ok=True, result=_to_jsonable(result))


def _to_jsonable(value: Any) -> Any:
    """Normalize facade return values into JSON-serialisable shapes.

    BackendFacade returns plain dicts/lists/tuples/bools/strings today, but
    ``tuple`` is not JSON and pyion events occasionally leak through — so
    coerce defensively.
    """
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def serve(
    *,
    rep_port: int,
    pub_port: int,
    facade: BackendFacade,
    bind_host: str = "*",
    stop_event: threading.Event | None = None,
) -> None:
    """Run the blocking IPC server.

    The container agent calls this on its main thread. ``stop_event`` is
    optional — when signalled, the loop exits and sockets are closed.
    Without it, SIGTERM / SIGINT set an internal event so ``docker stop``
    unwinds cleanly.
    """
    ctx = zmq.Context.instance()
    rep = ctx.socket(zmq.REP)
    pub = ctx.socket(zmq.PUB)

    rep_addr = f"tcp://{bind_host}:{rep_port}"
    pub_addr = f"tcp://{bind_host}:{pub_port}"
    rep.bind(rep_addr)
    pub.bind(pub_addr)
    logger.info("IPC server bound REP=%s PUB=%s", rep_addr, pub_addr)

    # Poll so we can exit on stop_event without blocking forever in recv.
    poller = zmq.Poller()
    poller.register(rep, zmq.POLLIN)

    pub_lock = threading.Lock()

    def publish(event: Event) -> None:
        # Multi-frame: topic first so subscribers can filter with SUBSCRIBE.
        with pub_lock:
            pub.send_multipart([event.topic.encode("utf-8"), event.to_json()])

    local_stop = stop_event or threading.Event()

    def _handle_signal(signum, _frame):
        logger.info("IPC server received signal %s, stopping", signum)
        local_stop.set()

    if stop_event is None:
        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

    try:
        while not local_stop.is_set():
            events = dict(poller.poll(timeout=500))
            if rep in events:
                try:
                    raw = rep.recv()
                    request = Request.from_json(raw)
                except Exception as exc:
                    # Malformed request: send a bad_request reply so the
                    # REP socket stays in the correct state for the next
                    # client.
                    logger.warning("malformed request: %s", exc)
                    reply = Reply(id="", ok=False, error=f"{ERR_BAD_REQUEST}: {exc}")
                    rep.send(reply.to_json())
                    continue

                reply = _dispatch(facade, request, publish)
                rep.send(reply.to_json())
    finally:
        rep.close(linger=0)
        pub.close(linger=0)
        logger.info("IPC server stopped")
