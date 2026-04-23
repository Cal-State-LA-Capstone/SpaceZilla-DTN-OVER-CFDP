"""Integration test for the full host <-> container IPC loop.

Unlike :mod:`tests.test_ipc_server_client` (which runs an in-process
fake facade), this actually boots a container via
:func:`backend.docker_backend.start_container`, connects with an
:class:`IpcClient` against the OS-assigned ports, and verifies the
in-container agent answers ``health`` and rejects unknown methods.
"""

from __future__ import annotations

import time
import uuid

import pytest

pytestmark = pytest.mark.integration

from backend.docker_backend import (  # noqa: E402
    build_image,
    start_container,
    stop_container,
)
from backend.ipc.client import IpcClient, IpcError  # noqa: E402
from store.models import NodeConfig  # noqa: E402


def _make_config() -> NodeConfig:
    return NodeConfig(
        node_id=f"ipc-{uuid.uuid4().hex[:8]}",
        name="ipc-test",
        ion_node_number=1,
        ion_entity_id=1,
        bp_endpoint="ipn:1.1",
    )


@pytest.fixture
def running_agent(docker_available):
    if not docker_available:
        pytest.skip("Docker not available")
    build_image()
    running = start_container(_make_config(), host_mount=False)

    # Poll health() for up to 20 s while ION + the agent come up.
    client = IpcClient(running.rep_port, running.pub_port)
    deadline = time.monotonic() + 20.0
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            result = client.health()
            if isinstance(result, dict) and result.get("ok"):
                break
        except IpcError as exc:
            last_err = exc
        time.sleep(1.0)
    else:
        client.close()
        stop_container(running.container_id)
        raise AssertionError(f"agent never became healthy: {last_err}")

    try:
        yield {"client": client, "running": running}
    finally:
        client.close()
        stop_container(running.container_id)


def test_health_ok(running_agent):
    assert running_agent["client"].health() == {"ok": True}


def test_unknown_method_returns_error(running_agent):
    client: IpcClient = running_agent["client"]
    with pytest.raises(IpcError) as exc:
        client.call("does_not_exist_in_facade")
    assert exc.value.error == "unknown_method"
