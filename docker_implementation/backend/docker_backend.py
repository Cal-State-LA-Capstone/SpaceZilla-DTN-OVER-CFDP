# backend/docker_backend.py
#
# Docker lifecycle helpers for ION containers.
#
# The controller (or higher-level backend logic) calls these to:
# - build the ION image
# - spin up per-node containers
# - tear them down
#
# Every function shells out to the docker CLI via subprocess.
#
# NOTE:
# This file was moved out of backend/__init__.py to avoid pulling in
# Docker and store dependencies when importing the backend for simple
# use cases (like the test UI).


from __future__ import annotations

import platform
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from runtime_logger import get_logger
from store.models import DockerStatus, NodeConfig

# Logger specific to Docker-related operations
logger = get_logger("docker_backend")

# -----------------------------
# Constants
# -----------------------------

# Name we tag the built image with
_IMAGE_NAME = "spacezilla-ion"

# Fixed ports inside the container for the REQ/REP + PUB IPC channel.
# The host maps both to ephemeral 127.0.0.1 ports via ``-p``.
_AGENT_REP_PORT = 5555
_AGENT_PUB_PORT = 5556


@dataclass
class RunningContainer:
    """Result of a successful :func:`start_container` call.

    ``rep_port`` / ``pub_port`` are the host-side ephemeral ports the OS
    assigned — resolved via ``docker port`` after ``docker run``.
    ``host_mount`` echoes whether the read-only ``/`` -> ``/host`` bind
    mount was applied.
    """

    container_id: str
    rep_port: int
    pub_port: int
    host_mount: bool


# Path to the Dockerfile lives one level up from backend/
# This assumes your project layout is:
#   project_root/
#     backend/
#     docker/
#       pyion_v414a2.dockerfile
_DOCKERFILE = (
    Path(__file__).resolve().parent.parent / "docker" / "pyion_v414a2.dockerfile"
)


# -----------------------------
# Image Build
# -----------------------------


def build_image(*, force: bool = False) -> None:
    """
    Build the ION Docker image if it does not already exist.

    Args:
        force: Rebuild even if the image is present.
    """
    if not force:
        # Quick check: does the image already exist locally?
        result = subprocess.run(
            ["docker", "images", "-q", _IMAGE_NAME],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            return  # already built, nothing to do

    logger.info(
        "Building Docker image '%s' (this may take a few minutes)...",
        _IMAGE_NAME,
    )

    # Run docker build command
    result = subprocess.run(
        [
            "docker",
            "build",
            "-t",
            _IMAGE_NAME,
            "-f",
            str(_DOCKERFILE),
            str(_DOCKERFILE.parent),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Surface the Docker error output for debugging
        raise RuntimeError(f"Docker image build failed: {result.stderr.strip()}")

    logger.info("Docker image '%s' built successfully", _IMAGE_NAME)


# -----------------------------
# Container Lifecycle
# -----------------------------


def _host_mount_args() -> list[str]:
    """Return the ``-v`` flags that bind-mount the host root at ``/host``.

    Linux / macOS get ``-v /:/host:ro,rslave`` — ``ro`` keeps the mount
    read-only so a compromised container cannot modify host files, and
    ``rslave`` propagates new sub-mounts (e.g. plugged-in drives) into
    the container without re-running. Windows Docker Desktop does not
    always allow a full-drive mount, so fall back to ``//./``; callers
    log a warning on failure.
    """
    system = platform.system()
    if system == "Windows":
        return ["-v", "//./:/host:ro"]
    return ["-v", "/:/host:ro,rslave"]


def start_container(
    config: NodeConfig,
    *,
    host_mount: bool = False,
) -> RunningContainer:
    """Run a detached container for this node and return its handles.

    Generates an ionstart.rc file from the node config, mounts it into
    the container, publishes the ZMQ agent ports to random 127.0.0.1
    ports, and launches ``backend.container_agent`` after ``ionstart``.

    Args:
        config: node configuration read from disk.
        host_mount: when True, adds the read-only ``/`` -> ``/host`` bind
            mount so the in-container pyion adapter can ``cfdp_send``
            host files in place without copying. The GUI only sets this
            after the user accepts the consent prompt.
    """
    # Import here to avoid circular imports or unnecessary dependency loading
    from backend.rc_generator import generate_rc

    # Use part of the node ID to create a unique container name
    container_name = f"spacezilla-{config.node_id[:12]}"

    # Remove any stale container with the same name from a previous run
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    # Generate ionstart.rc and write to a temp file on the host.
    # delete=False so it stays on disk while the container uses it.
    rc_content = generate_rc(config)
    rc_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".rc", prefix="ionstart_", delete=False
    )
    rc_file.write(rc_content)
    rc_file.close()

    logger.debug("Generated ionstart.rc at %s", rc_file.name)

    volume_args: list[str] = ["-v", f"{rc_file.name}:/home/ionstart.rc:ro"]
    if host_mount:
        volume_args.extend(_host_mount_args())
        logger.info("host bind mount enabled: %s", volume_args[-1])
    else:
        logger.info("host bind mount disabled (no consent)")

    agent_cmd = (
        f"ionstart -I /home/ionstart.rc && "
        f"python3 -m backend.container_agent "
        f"--rep-port {_AGENT_REP_PORT} --pub-port {_AGENT_PUB_PORT}"
    )

    # Launch container in detached mode
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "--cpus",
            "1.0",
            "--memory",
            "512m",
            # Pass configuration via environment variables
            "-e",
            f"ION_NODE_NUMBER={config.ion_node_number}",
            "-e",
            f"ION_ENTITY_ID={config.ion_entity_id}",
            "-e",
            f"BP_ENDPOINT={config.bp_endpoint}",
            # Publish the agent's REQ/REP + PUB ports on loopback-only
            # ephemeral host ports. Resolved via ``docker port`` below.
            "-p",
            f"127.0.0.1:0:{_AGENT_REP_PORT}",
            "-p",
            f"127.0.0.1:0:{_AGENT_PUB_PORT}",
            *volume_args,
            _IMAGE_NAME,
            # Start ION, then start the Python agent (replaces tail -f).
            "bash",
            "-c",
            agent_cmd,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # If the Windows full-drive mount failed, retry without it so the
        # user at least gets a running agent — transfers will need files
        # under explicitly-shared paths only.
        if host_mount and platform.system() == "Windows":
            logger.warning(
                "docker run failed with host_mount on Windows; "
                "retrying without the bind mount"
            )
            return start_container(config, host_mount=False)
        raise RuntimeError(
            f"docker run failed: {result.stderr.strip() or result.stdout.strip()}"
        )

    container_id = result.stdout.strip()

    try:
        rep_port = _resolve_port(container_id, _AGENT_REP_PORT)
        pub_port = _resolve_port(container_id, _AGENT_PUB_PORT)
    except Exception:
        # If we can't figure out the mapped ports, the container is
        # useless — tear it down so the caller doesn't leak it.
        stop_container(container_id)
        raise

    logger.info(
        "Container %s started (REP=%d PUB=%d host_mount=%s)",
        container_id[:12],
        rep_port,
        pub_port,
        host_mount,
    )

    return RunningContainer(
        container_id=container_id,
        rep_port=rep_port,
        pub_port=pub_port,
        host_mount=host_mount,
    )


def start_container_legacy(config: NodeConfig) -> str:
    """Deprecated compatibility shim.

    The removed path used a stringly-typed return value. Any call site
    still using it gets the container ID only; new code should use
    :func:`start_container` and read the full :class:`RunningContainer`.
    """
    running = start_container(config, host_mount=False)
    return running.container_id


# Regex matching one line of ``docker port <id> <port>/tcp`` output,
# e.g. ``0.0.0.0:49154`` or ``127.0.0.1:49155``. IPv6 lines are skipped.
_PORT_LINE_RE = re.compile(r"^(?:\d+\.){3}\d+:(\d+)$")


def _resolve_port(container_id: str, container_port: int) -> int:
    """Ask Docker which host port was assigned for ``container_port/tcp``.

    Returns the first IPv4 mapping. Raises ``RuntimeError`` if the
    command fails or produces no parseable line.
    """
    result = subprocess.run(
        ["docker", "port", container_id, f"{container_port}/tcp"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"docker port {container_id} {container_port}/tcp failed: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    for line in result.stdout.splitlines():
        match = _PORT_LINE_RE.match(line.strip())
        if match:
            return int(match.group(1))

    raise RuntimeError(
        f"no IPv4 mapping for {container_port}/tcp in: {result.stdout!r}"
    )


def stop_container(container_id: str) -> None:
    """
    Stop and remove a running container.
    """
    subprocess.run(["docker", "stop", container_id], capture_output=True)
    subprocess.run(["docker", "rm", container_id], capture_output=True)


def container_running(container_id: str) -> bool:
    """
    Check whether the given container is currently running.
    """
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            container_id,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


# -----------------------------
# Docker Startup Helpers
# -----------------------------


def _find_linux_docker_start_cmd() -> list[str] | None:
    """
    Figure out how to start Docker on this Linux system.

    Returns the systemctl command list, or None if we can't find one.

    Checks in order:
      1. docker.service  (docker-ce installed)
      2. podman.socket   (Fedora / RHEL — podman as Docker-compatible daemon)
    """
    for unit in ["docker.service", "podman.socket"]:
        result = subprocess.run(
            ["systemctl", "list-unit-files", unit],
            capture_output=True,
            text=True,
        )
        if unit in result.stdout:
            return ["pkexec", "systemctl", "start", unit]
    return None


def start_docker() -> DockerStatus:
    """
    Try to start the Docker/Podman daemon automatically.

    Cross-platform:
      - Linux: starts docker.service or podman.socket via pkexec
        (graphical password prompt)
      - macOS: opens Docker Desktop
      - Windows: opens Docker Desktop

    Waits up to ~20 seconds for the daemon to become ready.
    """
    system = platform.system()

    try:
        if system == "Linux":
            cmd = _find_linux_docker_start_cmd()
            if cmd is None:
                return DockerStatus(
                    available=False,
                    reason="not_installed",
                    message=(
                        "No Docker or Podman service found. "
                        "Install docker-ce or podman."
                    ),
                )
            subprocess.run(cmd, check=True)

        elif system == "Darwin":
            subprocess.run(["open", "-a", "Docker"], check=True)

        elif system == "Windows":
            subprocess.run(["cmd", "/c", "start", "", "Docker Desktop"], check=True)

    except (subprocess.CalledProcessError, FileNotFoundError):
        return DockerStatus(
            available=False,
            reason="start_failed",
            message="Could not start Docker automatically.",
        )

    # The daemon takes a few seconds to initialize.
    logger.info("Waiting for Docker daemon to start...")

    for _ in range(10):
        time.sleep(2)
        logger.debug("Docker not ready yet, retrying...")
        status = check_docker()
        if status.available:
            logger.info("Docker daemon is ready")
            return status

    logger.warning("Docker daemon did not start within expected time")

    return DockerStatus(
        available=False,
        reason="timeout",
        message="Docker was started but isn't ready yet. Try again.",
    )


def check_docker() -> DockerStatus:
    """
    Run `docker info` and determine Docker availability.
    """
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return DockerStatus.ok()

    stderr = result.stderr.lower()

    if "not found" in stderr or "no such file" in stderr:
        return DockerStatus(
            available=False,
            reason="missing",
            message="Docker is not installed.",
        )

    if "permission denied" in stderr:
        return DockerStatus(
            available=False,
            reason="permission_denied",
            message="Docker permission denied. Add user to docker group.",
        )

    return DockerStatus(
        available=False,
        reason="daemon_down",
        message="Docker daemon is not running.",
    )
