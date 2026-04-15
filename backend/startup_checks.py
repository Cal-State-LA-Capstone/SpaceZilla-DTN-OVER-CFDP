import os


def check_pyion() -> tuple[bool, str]:
    """
    Check if pyion can be imported.
    """
    try:
        import pyion  # noqa: F401

        return True, "pyion is available."
    except Exception as e:
        return False, f"pyion import failed: {e}"


def check_ion_env() -> tuple[bool, str]:
    """
    Check if basic ION environment variables exist.
    """
    ion_home = os.environ.get("ION_HOME")

    if not ion_home:
        return False, "ION_HOME is not set."

    return True, f"ION_HOME found: {ion_home}"


def run_all_checks() -> list[tuple[str, bool, str]]:
    """
    Run all startup checks.

    Returns:
        list of (check_name, success, message)
    """
    results = []

    checks = {
        "pyion": check_pyion,
        "ion_env": check_ion_env,
    }

    for name, func in checks.items():
        ok, msg = func()
        results.append((name, ok, msg))

    return results
