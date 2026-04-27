"""Generate ionstart.rc and live contact-plan rc content for an ION node.

The startup rc is generated from NodeConfig and contains the local node's
baseline configuration only.

Peer-specific routing/contact information is generated separately and applied
live via ionadmin/bpadmin/ipnadmin without restarting the node.
"""

from __future__ import annotations

from store.models import NodeConfig


def generate_rc(config: NodeConfig) -> str:
    """Generate ionstart.rc content for a single local ION node.

    Startup rc should define only this node's baseline identity and listeners.
    Peer contact plans should be added later via generate_contact_plan().
    """
    node_num = config.ion_node_number
    entity_id = config.ion_entity_id

    # Default host-side listener port scheme:
    # node1 -> 4556
    # node2 -> 4557
    # nodeN -> 4555 + N
    local_port = 4555 + int(node_num)

    return f"""\
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
a induct tcp 0.0.0.0:{local_port} tcpcli
s
## end bpadmin

## begin ipnadmin
## end ipnadmin

## begin cfdpadmin
1
a entity {entity_id} bp ipn:{node_num}.64 1 0 0
s bputa
## end cfdpadmin
"""


def generate_contact_plan(
    config: NodeConfig,
    peer_host: str,
    peer_num: int,
    peer_port: int = 4556,
) -> str:
    """Generate rc snippet to add a live contact plan."""
    node_num = config.ion_node_number
    peer_eid = f"ipn:{peer_num}.1"

    return f"""\
## begin ionadmin
a contact +1 +3600 {node_num} {peer_num} 100000
a contact +1 +3600 {peer_num} {node_num} 100000
a range +1 +3600 {node_num} {peer_num} 1
a range +1 +3600 {peer_num} {node_num} 1
## end ionadmin

## begin bpadmin
a outduct tcp {peer_host}:{peer_port} ''
s
## end bpadmin

## begin ipnadmin
a plan {peer_eid} tcp/{peer_host}:{peer_port}
## end ipnadmin
"""


def generate_remove_contact(
    config: NodeConfig,
    peer_host: str,
    peer_num: int,
    peer_port: int = 4556,
) -> str:
    """Generate rc snippet to remove a live contact plan."""
    node_num = config.ion_node_number
    peer_eid = f"ipn:{peer_num}.1"

    return f"""\
## begin ionadmin
d contact * {node_num} {peer_num} 
d contact * {peer_num} {node_num} 
d range * {node_num} {peer_num}
d range * {peer_num} {node_num} 
## end ionadmin

## begin bpadmin
d outduct tcp {peer_host}:{peer_port}
s
## end bpadmin

## begin ipnadmin
d plan {peer_eid}
## end ipnadmin
"""


# ---------------------------------------------------------------------
# OLD HARDCODED STARTUP TEMPLATE (DEPRECATED - kept for reference)
# ---------------------------------------------------------------------
# _RC_TEMPLATE = """\
# ## begin ionadmin
# 1 1 ''
# a contact +1 +3600 1 2 100000
# a contact +1 +3600 2 1 100000
# a range +1 +3600 1 2 1
# a range +1 +3600 2 1 1
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
# a endpoint ipn:1.0 q
# a endpoint ipn:1.1 q
# a endpoint ipn:1.2 q
# a endpoint ipn:1.64 q
# a endpoint ipn:1.65 q
# a protocol tcp 1400 100
# a induct tcp 0.0.0.0:4556 tcpcli
# a outduct tcp 127.0.0.1:4557 ''
# s
# ## end bpadmin
#
# ## begin ipnadmin
# a plan 2 tcp/127.0.0.1:4557
# ## end ipnadmin
#
# ## begin cfdpadmin
# 1
# a entity 1 bp ipn:1.64 1 0 0
# s bputa
# ## end cfdpadmin
# """