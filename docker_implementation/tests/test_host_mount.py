"""Integration tests for the host filesystem bind mount.

Verifies ``host_mount=True`` actually mounts the host root at ``/host``
(and ``host_mount=False`` doesn't) by shelling into the container with
``docker exec`` and reading a sentinel file written on the host.
"""

from __future__ import annotations

import subprocess
import time
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from backend.docker_backend import (  # noqa: E402
    build_image,
    start_container,
    stop_container,
)
from store.models import NodeConfig  # noqa: E402


def _make_config() -> NodeConfig:
    return NodeConfig(
        node_id=f"mt-{uuid.uuid4().hex[:8]}",
        name="mount-test",
        ion_node_number=1,
        ion_entity_id=1,
        bp_endpoint="ipn:1.1",
    )


@pytest.fixture
def image_built(docker_available):
    if not docker_available:
        pytest.skip("Docker not available")
    build_image()
    return True


def test_host_mount_exposes_host_files(image_built, tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("spacezilla-host-mount-ok")

    running = start_container(_make_config(), host_mount=True)
    try:
        time.sleep(1.0)  # let the container settle
        container_path = f"/host{sentinel}"
        result = subprocess.run(
            ["docker", "exec", running.container_id, "cat", container_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "spacezilla-host-mount-ok"
    finally:
        stop_container(running.container_id)


def test_no_host_mount_when_disabled(image_built) -> None:
    running = start_container(_make_config(), host_mount=False)
    try:
        time.sleep(1.0)
        result = subprocess.run(
            ["docker", "exec", running.container_id, "test", "-d", "/host"],
            capture_output=True,
            text=True,
        )
        # ``test -d`` returns non-zero when the directory does not exist.
        assert result.returncode != 0
    finally:
        stop_container(running.container_id)
