"""Shared fixtures for the SpaceZilla test suite."""

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
