"""In-container entry point for the SpaceZilla backend.

Runs as ``python3 -m backend.container_agent --rep-port N --pub-port M``
from ``start_container``'s CMD. Builds a :class:`BackendFacade` and
hands it to :func:`backend.ipc.server.serve`. The serve loop installs a
SIGTERM handler so ``docker stop`` unwinds cleanly.
"""

from __future__ import annotations

import argparse
import sys

from runtime_logger import get_logger, setup_logging

from backend.backend_facade import BackendFacade
from backend.ipc.server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="backend.container_agent")
    parser.add_argument("--rep-port", type=int, required=True)
    parser.add_argument("--pub-port", type=int, required=True)
    parser.add_argument("--bind-host", default="*")
    args = parser.parse_args(argv)

    setup_logging()
    logger = get_logger("container_agent")
    logger.info(
        "container_agent starting on REP=%d PUB=%d", args.rep_port, args.pub_port
    )

    facade = BackendFacade()
    serve(
        rep_port=args.rep_port,
        pub_port=args.pub_port,
        facade=facade,
        bind_host=args.bind_host,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
