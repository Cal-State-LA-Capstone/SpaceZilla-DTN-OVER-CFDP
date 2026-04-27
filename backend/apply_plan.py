"""Helpers for applying/removing live ION contact-plan updates.

Writes temp file, then applies ion commands for either delete or apply
"""

from __future__ import annotations

import subprocess
import tempfile

from runtime_logger import get_logger
from store.models import NodeConfig

logger = get_logger("backend")


def _apply_rc_text(rc_text: str, prefix: str) -> str:
    rc_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".rc",
        prefix=prefix,
        delete=False,
    )
    rc_file.write(rc_text)
    rc_file.close()
    logger.debug("Generated rc update file at %s", rc_file.name)

    for admin_cmd in ("ionadmin", "bpadmin", "ipnadmin"):
        result = subprocess.run(
            [admin_cmd, rc_file.name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"{admin_cmd} failed for {rc_file.name}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )

    logger.debug("Applied rc update content:\n%s", rc_text)
    return rc_file.name


def apply_contact_plan(config: NodeConfig, peer_host: str, peer_num: int, peer_port: int = 4556) -> None:
    from backend.rc_generator import generate_contact_plan

    rc_text = generate_contact_plan(
        config=config,
        peer_host=peer_host,
        peer_num=peer_num,
        peer_port=peer_port,
    )
    rc_path = _apply_rc_text(rc_text, prefix="update_plan_")
    logger.info(
        "Contact plan applied from %s (peer %s @ %s:%s)",
        rc_path,
        peer_num,
        peer_host,
        peer_port,
    )


def remove_contact_plan(config: NodeConfig, peer_host: str, peer_num: int, peer_port: int = 4556) -> None:
    """Generate and apply a live contact-plan removal for a peer."""
    from backend.rc_generator import generate_remove_contact

    rc_text = generate_remove_contact(
        config=config,
        peer_host=peer_host,
        peer_num=peer_num,
        peer_port=peer_port,
    )
    rc_path = _apply_rc_text(rc_text, prefix="remove_plan_")
    logger.info(
        "Contact plan removed from %s (peer %s @ %s:%s)",
        rc_path,
        peer_num,
        peer_host,
        peer_port,
    )