"""Runtime-tunable settings that can be changed from the admin panel.

Values live in the DB ``settings`` table and override the env/``.env`` defaults.
The scheduler and scraper manager read effective values here, so panel edits
take effect on the next run / reschedule without a restart.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from .config import settings
from .database import SessionLocal
from . import models

log = logging.getLogger(__name__)

_KEY = "runtime_overrides"

# Keys that may be changed at runtime.
EDITABLE = {
    "scraper_provider",        # mock | instagrapi
    "schedule_cron",
    "schedule_enabled",
    "per_handle_delay",
    "recent_media_count",
    "insta_username",
    "insta_password",
    "insta_proxy",
}

# Keys whose values are secrets (masked in API responses).
SECRET_KEYS = {"insta_password"}


def _load_overrides() -> dict:
    db = SessionLocal()
    try:
        row = db.get(models.Setting, _KEY)
        return dict(row.value) if row and isinstance(row.value, dict) else {}
    except Exception:  # noqa: BLE001 - table may not exist yet on first boot
        return {}
    finally:
        db.close()


_overrides: dict = _load_overrides()


def get(key: str) -> Any:
    if key in _overrides:
        return _overrides[key]
    return getattr(settings, key)


def apply(key: str, value: Any) -> None:
    if key not in EDITABLE:
        raise ValueError(f"Key {key!r} is not editable at runtime")
    _overrides[key] = value
    db = SessionLocal()
    try:
        row = db.get(models.Setting, _KEY)
        if row is None:
            row = models.Setting(key=_KEY, value=dict(_overrides))
            db.add(row)
        else:
            row.value = dict(_overrides)
        db.commit()
    finally:
        db.close()
    log.info("Runtime setting updated: %s", key)


def snapshot() -> dict:
    """Effective runtime settings for the UI (secrets masked)."""
    out: dict = {}
    for key in EDITABLE:
        val = get(key)
        if key in SECRET_KEYS and val:
            out[key] = "********"
        else:
            out[key] = val
    return out
