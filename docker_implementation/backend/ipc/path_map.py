"""Host <-> container path translation for the ``/host`` bind mount.

The container agent sees the host filesystem at ``/host`` (read-only,
opt-in). When the GUI picks a file from the host file system, every
path crossing the IPC boundary is rewritten with :func:`to_container_path`.
The inverse :func:`to_host_path` is used for display and logging so the
user still sees the path they chose.

Pure functions: no Docker, no disk access.
"""

from __future__ import annotations

import posixpath
import re

#: Directory inside the container where the host root is bind-mounted.
CONTAINER_ROOT: str = "/host"

_WINDOWS_DRIVE_RE = re.compile(r"^([a-zA-Z]):[\\/](.*)$")


def to_container_path(host_path: str) -> str:
    """Map a host-visible path into its ``/host/...`` container form.

    Examples:
        ``/home/alice/photo.jpg`` -> ``/host/home/alice/photo.jpg``
        ``C:\\Users\\alice\\photo.jpg`` -> ``/host/c/Users/alice/photo.jpg``
        ``/host/already/translated`` -> ``/host/already/translated``

    Already-translated paths are returned unchanged so the call is
    idempotent.
    """
    if not host_path:
        raise ValueError("host_path must not be empty")

    if host_path.startswith(CONTAINER_ROOT + "/") or host_path == CONTAINER_ROOT:
        return host_path

    windows_match = _WINDOWS_DRIVE_RE.match(host_path)
    if windows_match:
        drive = windows_match.group(1).lower()
        remainder = windows_match.group(2).replace("\\", "/")
        return posixpath.normpath(f"{CONTAINER_ROOT}/{drive}/{remainder}")

    # POSIX absolute path.
    if host_path.startswith("/"):
        return posixpath.normpath(f"{CONTAINER_ROOT}{host_path}")

    raise ValueError(f"host_path must be absolute: {host_path!r}")


def to_host_path(container_path: str) -> str:
    """Inverse of :func:`to_container_path`.

    Returns the input unchanged when it does not live under ``/host``.
    Drive letters are lower-cased and rewritten as Windows paths only
    when they look like single-character first segments under ``/host``.
    """
    if not container_path:
        raise ValueError("container_path must not be empty")

    if not container_path.startswith(CONTAINER_ROOT):
        return container_path

    # Strip the /host prefix, keep leading slash on the remainder.
    tail = container_path[len(CONTAINER_ROOT) :]
    if tail == "":
        return "/"
    if not tail.startswith("/"):
        # /hostfoo — not actually under the bind mount.
        return container_path

    # Windows: ``/host/c/Users/...`` -> ``C:/Users/...``
    segments = tail.lstrip("/").split("/", 1)
    if len(segments) == 2 and len(segments[0]) == 1 and segments[0].isalpha():
        drive = segments[0].upper()
        remainder = segments[1]
        return f"{drive}:/{remainder}"

    return tail
