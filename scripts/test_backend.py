#!/usr/bin/env python3
"""Quick smoke test for backend modules.
Run from project root: uv run --env-file lib.env scripts/test_backend.py
"""
import sys
from pathlib import Path

# make sure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test(name, fn):
    try:
        result = fn()
        print(f"PASS  {name}: {result}")
    except Exception as e:
        print(f"FAIL  {name}: {e}")


# 1. pyion import
test("pyion import", lambda: __import__("pyion"))

# 2. BackendFacade import
test("BackendFacade import", lambda: __import__("backend.facade", fromlist=["BackendFacade"]))

# 3. startup checks
def run_checks():
    from backend.facade import BackendFacade
    facade = BackendFacade()
    results = facade.startup_check()
    for name, ok, msg in results:
        status = "ok" if ok else "FAIL"
        print(f"       [{status}] {name}: {msg}")
    return "done"

test("startup checks", run_checks)

# 4. ION binaries on PATH
import subprocess
for cmd in ["ionadmin", "bpadmin", "ipnadmin", "cfdpadmin"]:
    test(f"{cmd} on PATH", lambda c=cmd: subprocess.run(
        ["which", c], capture_output=True, check=True
    ).stdout.decode().strip())