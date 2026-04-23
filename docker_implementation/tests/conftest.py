"""Shared fixtures for the SpaceZilla test suite."""

import subprocess
import sys
from pathlib import Path

import pytest

# Add the project root to sys.path so tests can import store/, frontend/, etc.
# These aren't installed packages — they're top-level directories in the repo.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture(autouse=True)
def store_dir(tmp_path, monkeypatch):
    """Redirect all store operations to a temp directory.

    Without this, tests would read/write to your real
    ~/.local/share/SpaceZilla/ directory. This fixture patches
    platformdirs so every test gets its own clean, isolated folder.
    """
    fake_data_dir = tmp_path / "spacezilla"
    monkeypatch.setattr(
        "platformdirs.user_data_path",
        lambda *_args, **_kwargs: fake_data_dir,
    )
    return fake_data_dir


@pytest.fixture(scope="session")
def docker_available() -> bool:
    """True if a Docker daemon is reachable.

    Used by the ``integration`` marker. Tests that need Docker should
    request this fixture and ``pytest.skip`` when it is False, so the
    suite still passes on CI / workstations without Docker.
    """
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
