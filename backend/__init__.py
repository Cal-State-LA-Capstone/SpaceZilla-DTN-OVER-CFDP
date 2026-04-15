"""Docker lifecycle helpers for ION containers.

The controller calls these to build the ION image, spin up
per-node containers, and tear them down. Every function shells
out to the docker CLI via subprocess.
"""

from __future__ import annotations

import platform
import subprocess
import threading
import tempfile
import time
from pathlib import Path

from runtime_logger import get_logger
from store.models import DockerStatus, NodeConfig

logger = get_logger("backend")

# Name we tag the built image with
_IMAGE_NAME = "spacezilla-ion"
# Path to the Dockerfile lives one level up from backend/
_DOCKERFILE = (
    Path(__file__).resolve().parent.parent / "docker" / "pyion_v414a2.dockerfile"
)


def build_image(*, force: bool = False) -> None:
    """Build the ION Docker image if it does not already exist.

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
        raise RuntimeError(f"Docker image build failed: {result.stderr.strip()}")
    logger.info("Docker image '%s' built successfully", _IMAGE_NAME)


def start_container(config: NodeConfig) -> str:
    """Run a detached container for this node. Returns the container ID.

    Generates an ionstart.rc file from the node config, mounts it
    into the container, and runs ionstart so ION is ready for PyION.
    """
    from backend.rc_generator import generate_rc

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
            "-e",
            f"ION_NODE_NUMBER={config.ion_node_number}",
            "-e",
            f"ION_ENTITY_ID={config.ion_entity_id}",
            "-e",
            f"BP_ENDPOINT={config.bp_endpoint}",
            # Mount the generated .rc file into the container
            "-v",
            f"{rc_file.name}:/home/ionstart.rc:ro",
            _IMAGE_NAME,
            # Start ION with the .rc file, then stay alive for PyION
            "bash",
            "-c",
            "ionstart -I /home/ionstart.rc && tail -f /dev/null",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"docker run failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def stop_container(container_id: str) -> None:
    """Stop and remove a running container."""
    subprocess.run(["docker", "stop", container_id], capture_output=True)
    subprocess.run(["docker", "rm", container_id], capture_output=True)


def container_running(container_id: str) -> bool:
    """Check whether the given container is currently running."""
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


def _find_linux_docker_start_cmd() -> list[str] | None:
    """Figure out how to start Docker on this Linux system.

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
    """Try to start the Docker/Podman daemon automatically.

    Cross-platform:
      - Linux: starts docker.service or podman.socket via pkexec
        (graphical password prompt)
      - macOS: opens Docker Desktop
      - Windows: opens Docker Desktop
    Waits up to 20 seconds for the daemon to become ready.
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

    logger.warning("Docker daemon did not start within 20 seconds")
    return DockerStatus(
        available=False,
        reason="timeout",
        message="Docker was started but isn't ready yet. Try again.",
    )


def check_docker() -> DockerStatus:
    """Run `docker info` and figure out what's wrong (if anything)."""
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return DockerStatus.ok()

    # Try to give a specific reason so the UI can show a helpful message
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
            message="Docker permission denied. Add your user to the docker group.",
        )
    return DockerStatus(
        available=False,
        reason="daemon_down",
        message="Docker daemon is not running.",
    )

def start_ion_logger(container_id: str) -> None:
    """Runs 'docker exec container_id tail -f in seperate thread forever!"""
    ion_logger = get_logger("ion-log")

    def _capture():
        process = subprocess.Popen(
            ["docker", "exec", container_id, "tail", "-f", "/home/ion.log"],
            stdout=subprocess.PIPE,
            text=True,
        )
        for line in process.stdout:
            ion_logger.info(line.strip())

    thread = threading.Thread(target=_capture, daemon=True)
    thread.start()
