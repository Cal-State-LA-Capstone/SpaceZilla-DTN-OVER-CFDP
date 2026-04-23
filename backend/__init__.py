"""ION process lifecycle helpers.

The controller calls these to start and stop the local ION node.
Replaces the Docker-based backend — ION runs directly on the host.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time

from runtime_logger import get_logger
from store.models import NodeConfig

logger = get_logger("backend")

# Track the running ION process
_ion_process: subprocess.Popen | None = None


def start_ion(config: NodeConfig) -> str:
    """Generate ionstart.rc and start the ION node process.

    Returns the rc file path as a handle identifying this node instance.
    """
    from backend.rc_generator import generate_rc

    rc_content = generate_rc(config)
    rc_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".rc", prefix="ionstart_", delete=False
    )
    rc_file.write(rc_content)
    rc_file.close()
    logger.debug("Generated ionstart.rc at %s", rc_file.name)

    global _ion_process
    _ion_process = subprocess.Popen(
        ["ionstart", "-I", rc_file.name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give ION a moment to initialize
    time.sleep(2)

    if _ion_process.poll() is not None:
        _, stderr = _ion_process.communicate()
        raise RuntimeError(f"ION failed to start: {stderr.decode().strip()}")

    logger.info("ION node started (pid %s)", _ion_process.pid)
    return rc_file.name


def stop_ion() -> None:
    """Stop the running ION node gracefully via ionstop."""
    global _ion_process

    subprocess.run(["killm"], capture_output=True)

    if _ion_process is not None:
        _ion_process.wait(timeout=10)
        _ion_process = None

    logger.info("ION node stopped")


def ion_running() -> bool:
    """Check whether the ION node process is still alive."""
    if _ion_process is None:
        return False
    return _ion_process.poll() is None


def apply_contact_plan(
    config: NodeConfig,
    peer_host: str,
    peer_num: int,
    peer_port: int = 4556,
) -> None:
    """Generate and apply a contact plan to the running ION node.

    Safe to call on a live node — updates outduct and plan without restart.
    Call again with new peer info to change the link.
    """
    from backend.rc_generator import generate_contact_plan

    plan_content = generate_contact_plan(config, peer_host, peer_num, peer_port)

    plan_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".rc", prefix="contact_plan_", delete=False
    )
    plan_file.write(plan_content)
    plan_file.close()
    logger.debug("Generated contact_plan.rc at %s", plan_file.name)

    for admin_cmd in ["ionadmin", "bpadmin", "ipnadmin"]:
        subprocess.run([admin_cmd, plan_file.name], capture_output=True)

    logger.debug("Generated contact plan content:\n%s", plan_content)
    print(plan_content)
    logger.info(
        "Contact plan applied (peer %s @ %s:%s)", peer_num, peer_host, peer_port
    )


def start_ion_logger() -> None:
    """Tail ion.log in a background thread and forward lines to the logger."""
    ion_logger = get_logger("ion-log")

    def _capture() -> None:
        ion_log = os.path.join(os.getcwd(), "ion.log")
        process = subprocess.Popen(
            ["tail", "-f", ion_log],
            stdout=subprocess.PIPE,
            text=True,
        )
        for line in process.stdout:
            ion_logger.info(line.strip())

    thread = threading.Thread(target=_capture, daemon=True)
    thread.start()