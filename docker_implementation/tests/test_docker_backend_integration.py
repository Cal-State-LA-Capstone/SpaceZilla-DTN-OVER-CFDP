"""Integration tests for :func:`backend.docker_backend.start_container`.

These require a real Docker daemon and the ``spacezilla-ion`` image.
Marked with ``integration`` so the default ``pytest -m "not integration"``
invocation skips them.
"""

from __future__ import annotations

import subprocess
import time
import uuid

import pytest

pytestmark = pytest.mark.integration

from backend.docker_backend import (  # noqa: E402
    RunningContainer,
    build_image,
    container_running,
    start_container,
    stop_container,
)
from store.models import NodeConfig  # noqa: E402


def _make_config() -> NodeConfig:
    node_id = f"test-{uuid.uuid4().hex[:8]}"
    return NodeConfig(
        node_id=node_id,
        name="test",
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


@pytest.fixture
def started(image_built):
    """Start a single container; tear it down after the test."""
    running = start_container(_make_config(), host_mount=False)
    try:
        yield running
    finally:
        stop_container(running.container_id)


def test_start_container_returns_running_dataclass(started):
    assert isinstance(started, RunningContainer)
    assert started.container_id
    assert started.rep_port > 0
    assert started.pub_port > 0
    assert started.host_mount is False


def test_container_is_running(started):
    # give the daemon a moment to settle after docker run
    time.sleep(1.0)
    assert container_running(started.container_id) is True


def test_ports_exposed_on_loopback(started):
    """``docker port`` should resolve to 127.0.0.1 mappings for 5555 / 5556."""
    for container_port in (5555, 5556):
        result = subprocess.run(
            ["docker", "port", started.container_id, f"{container_port}/tcp"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "127.0.0.1:" in result.stdout, result.stdout


def test_stop_removes_container(image_built):
    running = start_container(_make_config(), host_mount=False)
    stop_container(running.container_id)
    # ``docker inspect`` should now fail because the container is gone.
    result = subprocess.run(
        ["docker", "inspect", running.container_id],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
