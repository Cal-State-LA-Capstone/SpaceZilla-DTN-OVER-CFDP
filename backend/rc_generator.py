"""Generate ionstart.rc content for an ION node.

The template is a basic single-node config with BPv7 and CFDP.
To add new ION features, add sections to _RC_TEMPLATE and
corresponding fields to store/rc_fields.py.

The format is documented in the ION-DTN manual:
https://github.com/nasa-jpl/ION-DTN
"""

from __future__ import annotations

from store.models import NodeConfig

# Minimal template for a single ION node running BP (LTP) and CFDP.
# Placeholders: {node_num}, {entity_id}, {peer_address}
# peer_address is where LTP sends outgoing packets (the remote node's IP:port).
# entity_id is the CFDP/BP node number of the destination
# (equals node_num for loopback).
_RC_TEMPLATE = """\
## begin ionadmin
1 {node_num} ''
s
a contact +1 +3600 {node_num} {entity_id} 100000
a range +1 +3600 {node_num} {entity_id} 0
m production 1000000
m consumption 1000000
## end ionadmin

## begin ltpadmin
1 32
a span {entity_id} 32 32 1400 10000 1 'udplso {peer_address}'
s 'udplsi 0.0.0.0:1113'
## end ltpadmin

## begin bpadmin
1
a scheme ipn 'ipnfw' 'ipnadminep'
a endpoint ipn:{node_num}.0 q
a endpoint ipn:{node_num}.1 q
a endpoint ipn:{node_num}.64 q
a endpoint ipn:{node_num}.65 q
a protocol ltp 1400 100
a induct ltp {node_num} ltpcli
a outduct ltp {entity_id} ltpclo
s
## end bpadmin

## begin ipnadmin
a plan {entity_id} ltp/{entity_id}
## end ipnadmin

## begin cfdpadmin
1
a entity {entity_id} bp ipn:{entity_id}.64 1 0 0
s bputa
## end cfdpadmin
"""


_RECEIVER_RC_TEMPLATE = """\
## begin ionadmin
1 {receiver_node_num} ''
s
a contact +1 +3600 {sender_node_num} {receiver_node_num} 100000
a contact +1 +3600 {receiver_node_num} {sender_node_num} 100000
a range +1 +3600 {sender_node_num} {receiver_node_num} 0
a range +1 +3600 {receiver_node_num} {sender_node_num} 0
m production 1000000
m consumption 1000000
## end ionadmin

## begin ltpadmin
1 32
a span {sender_node_num} 32 32 1400 10000 1 'udplso {sender_ip}:1113'
s 'udplsi 0.0.0.0:{receiver_ltp_port}'
## end ltpadmin

## begin bpadmin
1
a scheme ipn 'ipnfw' 'ipnadminep'
a endpoint ipn:{receiver_node_num}.0 q
a endpoint ipn:{receiver_node_num}.1 q
a endpoint ipn:{receiver_node_num}.64 q
a endpoint ipn:{receiver_node_num}.65 q
a protocol ltp 1400 100
a induct ltp {receiver_node_num} ltpcli
a outduct ltp {sender_node_num} ltpclo
s
## end bpadmin

## begin ipnadmin
a plan {sender_node_num} ltp/{sender_node_num}
## end ipnadmin

## begin cfdpadmin
1
a entity {sender_node_num} bp ipn:{sender_node_num}.64 1 0 0
s bputa
## end cfdpadmin
"""


def generate_receiver_rc(config: NodeConfig, sender_ip: str) -> str:
    """Generate a receiver-side ionstart.rc from the sender's node config.

    The receiver config is the mirror image: it listens on the port the
    sender's peer_address points to, and sends LTP ACKs back to sender_ip:1113
    (the port the sender's Docker container publishes).
    """
    fields = {f.name: f.value for f in config.rc_fields}
    sender_node_num = fields.get("node_number", config.ion_node_number)
    receiver_node_num = fields.get("entity_id", config.ion_entity_id)
    peer_address = fields.get("peer_address", "")
    try:
        receiver_ltp_port = peer_address.split(":")[1]
    except IndexError:
        receiver_ltp_port = "1114"

    return _RECEIVER_RC_TEMPLATE.format(
        sender_node_num=sender_node_num,
        receiver_node_num=receiver_node_num,
        sender_ip=sender_ip,
        receiver_ltp_port=receiver_ltp_port,
    )


def generate_rc(config: NodeConfig) -> str:
    """Fill in the ionstart.rc template from a node's config.

    Returns the file content as a string. The caller writes it
    to disk or mounts it into the container.
    """
    fields = {f.name: f.value for f in config.rc_fields}
    node_num = fields.get("node_number", config.ion_node_number)
    entity_id = fields.get("entity_id", config.ion_entity_id)
    peer_address = fields.get("peer_address", "").strip()
    if not peer_address:
        raise ValueError("peer_address is required (e.g. 192.168.1.50:1114)")

    return _RC_TEMPLATE.format(
        node_num=node_num,
        entity_id=entity_id,
        peer_address=peer_address,
    )
