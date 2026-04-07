"""Field definitions for the ionstart.rc configuration form.

The Node Picker reads RC_FIELDS to dynamically build its form.
Each entry has a name, label, type ("int", "str", or "bool"),
and default value. Add new fields here to extend the form.
"""

from __future__ import annotations

from typing import Any

RcFieldSpec = dict[str, Any]
"""Type alias for a single field spec dictionary."""

RC_FIELDS: list[RcFieldSpec] = [
    {
        "name": "node_number",
        "label": "ION Node Number",
        "type": "int",
        "default": 1,
    },
    {
        "name": "entity_id",
        "label": "CFDP Entity ID",
        "type": "int",
        "default": 1,
    },
    {
        "name": "bp_endpoint",
        "label": "BP Endpoint",
        "type": "str",
        "default": "ipn:1.1",
    },
    {
        "name": "node_name",
        "label": "Node Name",
        "type": "str",
        "default": "",
    },
    {
        "name": "service_count",
        "label": "Number of Services",
        "type": "int",
        "default": 1,
    },
]
