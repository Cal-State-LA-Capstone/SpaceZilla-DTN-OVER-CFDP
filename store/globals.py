"""Boot-time global reads from the shared settings directory."""

from __future__ import annotations

from store.models import GlobalSettings


def load_settings() -> GlobalSettings:
    """Read global/settings.json and return a GlobalSettings instance.

    Returns defaults if the file does not exist.
    """
    raise NotImplementedError


def load_theme(theme_name: str) -> dict[str, str]:
    """Read a theme definition from global/themes/{theme_name}.json.

    Returns a dict mapping widget role names to color strings.
    """
    raise NotImplementedError
