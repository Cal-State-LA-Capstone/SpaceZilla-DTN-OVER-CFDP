def parse_eid(eid: str) -> tuple[int, int]:
    """
    Parse an ION-style EID of the form 'ipn:node.service'.

    Returns:
        tuple[int, int]: (node_number, service_number)

    Raises:
        ValueError: If the EID format is invalid.
    """
    if not isinstance(eid, str):
        raise ValueError("EID must be a string.")

    eid = eid.strip()
    if not eid:
        raise ValueError("EID cannot be empty.")

    try:
        scheme, rest = eid.split(":", 1)
        node_str, service_str = rest.split(".", 1)
    except ValueError:
        raise ValueError(f"Invalid EID format: {eid}")

    if scheme != "ipn":
        raise ValueError(f"Unsupported EID scheme: {scheme}")

    try:
        node_number = int(node_str)
        service_number = int(service_str)
    except ValueError:
        raise ValueError(f"EID node and service must be integers: {eid}")

    if node_number < 0 or service_number < 0:
        raise ValueError(f"EID node and service must be non-negative: {eid}")

    return node_number, service_number


def is_valid_eid(eid: str) -> bool:
    """
    Return True if the EID is valid, else False.
    """
    try:
        parse_eid(eid)
        return True
    except ValueError:
        return False


def normalize_eid(eid: str) -> str:
    """
    Normalize an EID into canonical 'ipn:node.service' form.

    Examples:
        ' ipn:001.002 ' -> 'ipn:1.2'
    """
    node_number, service_number = parse_eid(eid)
    return f"ipn:{node_number}.{service_number}"


def split_eid(eid: str) -> dict[str, int | str]:
    """
    Return a dictionary representation of the EID.
    """
    normalized = normalize_eid(eid)
    node_number, service_number = parse_eid(normalized)

    return {
        "eid": normalized,
        "node_number": node_number,
        "service_number": service_number,
    }
