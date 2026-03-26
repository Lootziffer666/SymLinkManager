"""Persistent user settings for Tabula (tabula_settings.json next to the exe / app root)."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_APP_ROOT = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[1]
)
_SETTINGS_FILE = _APP_ROOT / "tabula_settings.json"

_DEFAULTS: dict = {
    "extra_search_paths": [],
}


def load() -> dict:
    """Return the current settings dict (merged with defaults)."""
    if _SETTINGS_FILE.exists():
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = dict(_DEFAULTS)
                merged.update(data)
                return merged
        except Exception as exc:
            logger.warning("tabula_settings.json unreadable, using defaults: %s", exc)
    return dict(_DEFAULTS)


def save(data: dict) -> None:
    """Persist *data* to tabula_settings.json."""
    try:
        _SETTINGS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:
        logger.error("Could not save tabula_settings.json: %s", exc)
