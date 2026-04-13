"""Docker lifecycle helpers for ION containers.

The controller calls these to build the ION image, spin up
per-node containers, and tear them down. Every function shells
out to the docker CLI via subprocess.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from store.models import DockerStatus, NodeConfig

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

    subprocess.run(
        [
            "docker",
            "build",
            "-t",
            _IMAGE_NAME,
            "-f",
            str(_DOCKERFILE),
            str(_DOCKERFILE.parent),
        ],
        check=True,
    )


def start_container(config: NodeConfig) -> str:
    """Run a detached container for this node. Returns the container ID."""
    # Container name uses the first 12 chars of the node_id so it's
    # recognizable in `docker ps` but still unique enough.
    container_name = f"spacezilla-{config.node_id[:12]}"
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",  # detached
            "--name",
            container_name,
            "--cpus",
            "1.0",  # limit to 1 CPU core
            "--memory",
            "512m",  # limit to 512 MB RAM
            # Pass ION config as env vars so the container can
            # set up its node on startup.
            "-e",
            f"ION_NODE_NUMBER={config.ion_node_number}",
            "-e",
            f"ION_ENTITY_ID={config.ion_entity_id}",
            "-e",
            f"BP_ENDPOINT={config.bp_endpoint}",
            _IMAGE_NAME,
        ],
        capture_output=True,
        text=True,
        check=True,
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
