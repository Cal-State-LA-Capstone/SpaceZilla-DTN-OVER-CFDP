"""Boot-time global reads from the shared settings directory."""

from __future__ import annotations

import dataclasses
import json

from store.models import GlobalSettings
from store.paths import global_dir, settings_path


def load_settings() -> GlobalSettings:
    """Read global/settings.json and return a GlobalSettings instance.

    Returns defaults if the file does not exist. Unknown keys in the file
    are ignored so older on-disk settings keep loading after new fields
    are added.
    """
    path = settings_path()
    if not path.exists():
        return GlobalSettings()
    data = json.loads(path.read_text())
    known = {f.name for f in dataclasses.fields(GlobalSettings)}
    filtered = {k: v for k, v in data.items() if k in known}
    return GlobalSettings(**filtered)


def save_settings(settings: GlobalSettings) -> None:
    """Write ``settings`` to global/settings.json (overwriting any prior file)."""
    path = settings_path()
    path.write_text(json.dumps(dataclasses.asdict(settings), indent=2))


def load_theme(theme_name: str) -> dict[str, str]:
    """Read a theme definition from global/themes/{theme_name}.json.

    Returns a dict mapping widget role names to color strings.
    """
    path = global_dir() / "themes" / f"{theme_name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())
