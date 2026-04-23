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

# Bare minimum template for a single ION node running BP (TCP) and CFDP.
# Placeholders: {node_num}, {entity_id}
_RC_TEMPLATE = """\
## begin ionadmin
1 {node_num} ''
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
a endpoint ipn:{node_num}.0 q
a endpoint ipn:{node_num}.1 q
a endpoint ipn:{node_num}.2 q
a endpoint ipn:{node_num}.64 q
a endpoint ipn:{node_num}.65 q
a protocol tcp 1400 100
a induct tcp 0.0.0.0:4556 tcpcli
s
## end bpadmin

## begin ipnadmin
## end ipnadmin

## begin cfdpadmin
1
a entity {entity_id} bp ipn:{entity_id}.64 1 0 0
s bputa
## end cfdpadmin
"""

# Contact plan template — applied live when a contact is added.
# Placeholders: {node_num}, {peer_num}, {peer_host}, {peer_port}, {peer_eid}
_CONTACT_PLAN_TEMPLATE = """\
## begin ionadmin
a contact +1 +3600 {node_num} {peer_num} 100000
a contact +1 +3600 {peer_num} {node_num} 100000
a range +1 +3600 {node_num} {peer_num} 1
a range +1 +3600 {peer_num} {node_num} 1
## end ionadmin

## begin bpadmin
a outduct tcp {peer_host}:{peer_port} ''
## end bpadmin

## begin ipnadmin
# CHANGED:
# Use a full EID, not a bare node number.
# WHY:
# ION rejected lines like `a plan 2 tcp/localhost:4557` with
# "Malformed EID: 2". ipnadmin expects a valid EID target.
a plan {peer_eid} tcp/{peer_host}:{peer_port}
## end ipnadmin
"""

# Contact removal template — applied live when a contact is removed.
# Placeholders: {node_num}, {peer_num}, {peer_host}, {peer_port}, {peer_eid}
_REMOVE_CONTACT_TEMPLATE = """\
## begin ionadmin
d contact +1 {node_num} {peer_num}
d contact +1 {peer_num} {node_num}
d range +1 {node_num} {peer_num}
d range +1 {peer_num} {node_num}
## end ionadmin

## begin bpadmin
d outduct tcp {peer_host}:{peer_port}
## end bpadmin

## begin ipnadmin
# CHANGED:
# Delete the same full EID-based plan we added.
# WHY:
# Keep add/remove symmetrical and valid for ipnadmin.
d plan {peer_eid}
## end ipnadmin
"""


def generate_rc(config: NodeConfig) -> str:
    """Fill in the ionstart.rc template from a node's config.

    Returns the file content as a string. Written to a temp file
    and passed to ionstart on boot.
    """
    fields = {f.name: f.value for f in config.rc_fields}
    node_num = fields.get("node_number", config.ion_node_number)
    entity_id = fields.get("entity_id", config.ion_entity_id)

    return _RC_TEMPLATE.format(
        node_num=node_num,
        entity_id=entity_id,
    )


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