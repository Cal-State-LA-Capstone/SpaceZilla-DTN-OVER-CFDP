"""End-to-end CFDP transfer between two SpaceZilla containers.

This test is the hardest integration surface: it needs two containers
sharing a user-defined bridge network, each with an ionstart.rc that
advertises the other peer's TCP CLA. The current
:mod:`backend.rc_generator` emits a single-node rc without peer CLA
entries, so the full two-node flow is not yet supported — the test is
skipped until :mod:`backend.rc_generator` learns to emit peer CLAs.

When that lands, re-enable the body below and it should:

    1. ``docker network create spacezilla-test`` (or reuse).
    2. start two containers with ``host_mount=True``, attached to the
       network with container names ``spacezilla-node1`` / ``node2``.
    3. write a sentinel file on the host, translate the path, queue it
       on node1 via :class:`backend.ipc.client.IpcClient`.
    4. poll ``client1.get_queue`` until the status is ``Completed``.
    5. ``docker exec`` node2 and assert ``/SZ_received_files/<name>``
       contains the sentinel bytes.
    6. mutate the host file between sends to prove the bind mount is
       in-place (no pre-copy).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(
    reason=(
        "Requires rc_generator support for peer TCP CLA entries; see "
        "module docstring for the checklist."
    )
)
def test_cfdp_transfer_two_nodes() -> None:
    raise NotImplementedError
