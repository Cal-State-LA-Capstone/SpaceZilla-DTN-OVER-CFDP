"""Wire protocol for the host <-> container ZMQ IPC channel.

The channel has two sockets:

- **REQ/REP** (commands): the host sends a :class:`Request`, the container
  runs the named method on its ``BackendFacade`` and replies with a
  :class:`Reply`.
- **PUB/SUB** (events): the container publishes :class:`Event` messages as
  the CFDP transfer pipeline advances. The host subscribes and forwards the
  updates into the Qt event loop.

All messages are UTF-8 JSON. Keep this module dependency-free so both the
host-side client and the in-container agent can import it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

# -- Topic strings --------------------------------------------------------
# PUB/SUB topic prefix for CFDP transfer status events.
TOPIC_CFDP: str = "cfdp"


# -- Method whitelist -----------------------------------------------------
# Any method name the host is allowed to call on ``BackendFacade``.
# ``server.serve`` rejects anything not in this set with ``unknown_method``.
METHODS: frozenset[str] = frozenset(
    {
        "health",
        "startup_check",
        "connect",
        "disconnect",
        "is_connected",
        "queue_files",
        "remove_file",
        "clear_queue",
        "get_queue",
        "send_files",
        "status_indicator",
    }
)


# -- Error codes ----------------------------------------------------------
ERR_UNKNOWN_METHOD: str = "unknown_method"
ERR_BAD_REQUEST: str = "bad_request"
ERR_EXCEPTION: str = "exception"


# -- Message shapes -------------------------------------------------------


@dataclass
class Request:
    """Host -> container command.

    ``id`` lets the host correlate replies; the server echoes it back.
    """

    id: str
    method: str
    args: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")

    @classmethod
    def from_json(cls, data: bytes) -> Request:
        obj = json.loads(data.decode("utf-8"))
        return cls(
            id=str(obj["id"]),
            method=str(obj["method"]),
            args=dict(obj.get("args") or {}),
        )


@dataclass
class Reply:
    """Container -> host reply to a :class:`Request`.

    ``ok`` is True for a normal return; False when ``error`` is set.
    """

    id: str
    ok: bool
    result: Any = None
    error: str | None = None

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")

    @classmethod
    def from_json(cls, data: bytes) -> Reply:
        obj = json.loads(data.decode("utf-8"))
        return cls(
            id=str(obj["id"]),
            ok=bool(obj["ok"]),
            result=obj.get("result"),
            error=obj.get("error"),
        )


@dataclass
class Event:
    """Asynchronous container -> host notification.

    Published on the PUB socket with the topic as the first ZMQ frame so
    subscribers can filter server-side.
    """

    topic: str
    queue_id: str
    status: str

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")

    @classmethod
    def from_json(cls, data: bytes) -> Event:
        obj = json.loads(data.decode("utf-8"))
        return cls(
            topic=str(obj["topic"]),
            queue_id=str(obj["queue_id"]),
            status=str(obj["status"]),
        )
