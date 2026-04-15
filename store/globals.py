"""Boot-time global reads from the shared settings directory."""

from __future__ import annotations

import json

from store.models import GlobalSettings
from store.paths import global_dir, settings_path


def load_settings() -> GlobalSettings:
    """Read global/settings.json and return a GlobalSettings instance.

    Returns defaults if the file does not exist.
    """
    path = settings_path()
    if not path.exists():
        return GlobalSettings()
    data = json.loads(path.read_text())
    return GlobalSettings(**data)


def load_theme(theme_name: str) -> dict[str, str]:
    """Read a theme definition from global/themes/{theme_name}.json.

    Returns a dict mapping widget role names to color strings.
    """
    path = global_dir() / "themes" / f"{theme_name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())
