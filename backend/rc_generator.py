"""Generate ionstart.rc and contact plan rc content for an ION node.

The ionstart.rc template covers the bare minimum to boot a node:
ionadmin, bpadmin (TCP only), ipnadmin, cfdpadmin.

Contact plans are generated separately and applied live via
ionadmin/bpadmin/ipnadmin without restarting the node.

The format is documented in the ION-DTN manual:
https://github.com/nasa-jpl/ION-DTN
"""

from __future__ import annotations

from store.models import NodeConfig

# -----------------------------------------------------------------------------
# ORIGINAL TEMPLATE (commented out for now)
# -----------------------------------------------------------------------------
# CHANGED:
# Keeping the original startup template here for reference, but disabling it
# during the current hardcoded send test phase.
# WHY:
# Right now you want one known-good startup config to prove host-based sending
# works before making rc generation dynamic again.
#
# _RC_TEMPLATE = """\
# ## begin ionadmin
# 1 {node_num} ''
# s
# m production 1000000
# m consumption 1000000
# m horizon +0
# ## end ionadmin
#
# ## begin ionsecadmin
# 1
# ## end ionsecadmin
#
# ## begin bpadmin
# 1
# a scheme ipn 'ipnfw' 'ipnadminep'
# a endpoint ipn:{node_num}.0 q
# a endpoint ipn:{node_num}.1 q
# a endpoint ipn:{node_num}.2 q
# a endpoint ipn:{node_num}.64 q
# a endpoint ipn:{node_num}.65 q
# a protocol tcp 1400 100
# a induct tcp 0.0.0.0:4556 tcpcli
# s
# ## end bpadmin
#
# ## begin ipnadmin
# ## end ipnadmin
#
# ## begin cfdpadmin
# 1
# a entity {entity_id} bp ipn:{entity_id}.64 1 0 0
# s bputa
# ## end cfdpadmin
# """

# -----------------------------------------------------------------------------
# TEMPORARY HARDCODED STARTUP TEMPLATE
# -----------------------------------------------------------------------------
# CHANGED:
# This template is intentionally hardcoded for the current local send test.
# WHY:
# You want one deterministic known-good config before returning to dynamic
# generation and contact-plan/UI integration.
#
# Assumptions for this temporary template:
# - App-controlled node is node 1 / entity 1
# - Peer is node 2 on localhost
# - Peer listens on TCP port 4557
# - Local node listens on TCP port 4556
#
# NOTE:
# This is temporary test scaffolding, not the final architecture.
_RC_TEMPLATE = """\
## begin ionadmin
1 1 ''
a contact +1 +3600 1 2 100000
a contact +1 +3600 2 1 100000
a range +1 +3600 1 2 1
a range +1 +3600 2 1 1
s
m production 1000000
m consumption 1000000
m horizon +0
## end ionadmin

## begin ionsecadmin
1
## end ionsecadmin

## begin bpadmin
1
a scheme ipn 'ipnfw' 'ipnadminep'
a endpoint ipn:1.0 q
a endpoint ipn:1.1 q
a endpoint ipn:1.2 q
a endpoint ipn:1.64 q
a endpoint ipn:1.65 q
a protocol tcp 1400 100
a induct tcp 0.0.0.0:4556 tcpcli
a outduct tcp 127.0.0.1:4557 ''
s
## end bpadmin

## begin ipnadmin
a plan 2 tcp/127.0.0.1:4557
## end ipnadmin

## begin cfdpadmin
1
a entity 1 bp ipn:1.64 1 0 0
s bputa
## end cfdpadmin
"""


def generate_rc(config: NodeConfig) -> str:
    """Return a temporary hardcoded startup rc for send testing.

    CHANGED:
    This currently ignores NodeConfig values.
    WHY:
    The current goal is to prove one deterministic send path works before
    restoring dynamic config generation.
    """
    return _RC_TEMPLATE


def generate_contact_plan(
    config: NodeConfig,
    peer_host: str,
    peer_num: int,
    peer_port: int = 4556,
) -> str:
    """Generate a contact plan rc for linking this node to a peer.

    Applied to a running ION node without restarting.
    Call again with updated peer info to change the link.
    """
    fields = {f.name: f.value for f in config.rc_fields}
    node_num = fields.get("node_number", config.ion_node_number)

    # ADDED:
    # Build a valid destination EID for ipnadmin.
    # WHY:
    # A bare peer number like `2` is not a valid EID.
    # Service `.0` matches the node-level endpoint used in routing plans.
    peer_eid = f"ipn:{peer_num}.0"

    return _CONTACT_PLAN_TEMPLATE.format(
        node_num=node_num,
        peer_num=peer_num,
        peer_host=peer_host,
        peer_port=peer_port,
        peer_eid=peer_eid,
    )


def generate_remove_contact(
    config: NodeConfig,
    peer_host: str,
    peer_num: int,
    peer_port: int = 4556,
) -> str:
    """Generate an rc to remove a contact plan for a peer.

    Applied to a running ION node without restarting.
    """
    fields = {f.name: f.value for f in config.rc_fields}
    node_num = fields.get("node_number", config.ion_node_number)

    # ADDED:
    # Must match the EID format used when adding the plan.
    peer_eid = f"ipn:{peer_num}.0"

    return _REMOVE_CONTACT_TEMPLATE.format(
        node_num=node_num,
        peer_num=peer_num,
        peer_host=peer_host,
        peer_port=peer_port,
        peer_eid=peer_eid,
    )