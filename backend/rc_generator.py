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
# Placeholders: {node_num}, {entity_id}, {service_count}
_RC_TEMPLATE = """\
## begin ionadmin
1 {node_num} ''
s
a contact +1 +3600 {node_num} {node_num} 100000
a range +1 +3600 {node_num} {node_num} 0
m production 1000000
m consumption 1000000
## end ionadmin

## begin ltpadmin
1 32
a span {node_num} 32 32 1400 10000 1 'udplso 127.0.0.1:1113'
s 'udplsi 127.0.0.1:1113'
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
a outduct ltp {node_num} ltpclo
s
## end bpadmin

## begin ipnadmin
a plan {node_num} ltp/{node_num}
## end ipnadmin

## begin cfdpadmin
1
a entity {node_num} bp ipn:{node_num}.64 1 0 0
s bputa
## end cfdpadmin
"""


def generate_rc(config: NodeConfig) -> str:
    """Fill in the ionstart.rc template from a node's config.

    Returns the file content as a string. The caller writes it
    to disk or mounts it into the container.
    """
    fields = {f.name: f.value for f in config.rc_fields}
    node_num = fields.get("node_number", config.ion_node_number)
    entity_id = fields.get("entity_id", config.ion_entity_id)
    service_count = fields.get("service_count", 1)

    return _RC_TEMPLATE.format(
        node_num=node_num,
        entity_id=entity_id,
        service_count=service_count,
    )
