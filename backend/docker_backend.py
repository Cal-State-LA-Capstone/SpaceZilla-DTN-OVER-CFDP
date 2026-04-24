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
import socket
import subprocess
import tempfile
import time
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

# Path to the Dockerfile lives one level up from backend/
# This assumes your project layout is:
#   project_root/
#     backend/
#     docker/
#       pyion_v414a2.dockerfile
_DOCKERFILE = (
    Path(__file__).resolve().parent.parent / "docker" / "pyion_v414a2.dockerfile"
)

_ION_SERVER = (
    Path(__file__).resolve().parent.parent / "docker" / "ion_server.py"
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


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def wait_for_ion_server(port: int, timeout: float = 40.0) -> bool:
    """Poll until ion_server inside the container is accepting HTTP connections."""
    import httpx

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/connected", timeout=2.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1.5)
    return False


def start_container(config: NodeConfig) -> tuple[str, int]:
    """
    Run a detached container for this node. Returns (container_id, ion_server_port).

    Generates an ionstart.rc file from the node config, mounts it into the
    container, runs ionstart, then starts ion_server.py for HTTP-based CFDP.
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

    ion_server_port = _find_free_port()
    home_dir = str(Path.home())

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
            # Allow container to reach the host machine as host.docker.internal
            "--add-host=host.docker.internal:host-gateway",
            # Forward ion_server HTTP port
            "-p",
            f"{ion_server_port}:8765",
            # Mount .rc file, ion_server script, and user home dir for file access
            "-v",
            f"{rc_file.name}:/home/ionstart.rc:ro",
            "-v",
            f"{_ION_SERVER}:/home/ion_server.py:ro",
            "-v",
            f"{home_dir}:{home_dir}:ro",
            _IMAGE_NAME,
            # Start ION then launch the HTTP bridge
            "bash",
            "-c",
            "mkdir -p /SZ_received_files && ionstart -I /home/ionstart.rc && python3 /home/ion_server.py",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"docker run failed: {result.stderr.strip() or result.stdout.strip()}"
        )

    container_id = result.stdout.strip()
    logger.debug("Waiting for ion_server on port %s...", ion_server_port)

    if not wait_for_ion_server(ion_server_port):
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        raise RuntimeError("ion_server did not start within the timeout period")

    logger.info("ion_server ready on port %s", ion_server_port)
    return container_id, ion_server_port


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
