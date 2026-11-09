"""Runtime settings endpoints (cron, credentials, provider)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import runtime_config
from ..scraper.manager import manager
from .deps import require_auth

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_auth)])


class SettingsPatch(BaseModel):
    scraper_provider: Optional[str] = None
    schedule_cron: Optional[str] = None
    schedule_enabled: Optional[bool] = None
    per_handle_delay: Optional[float] = None
    recent_media_count: Optional[int] = None
    insta_username: Optional[str] = None
    insta_password: Optional[str] = None
    insta_proxy: Optional[str] = None


@router.get("")
def get_settings():
    return {
        "settings": runtime_config.snapshot(),
        "editable": sorted(runtime_config.EDITABLE),
        "health": manager.healthcheck(),
    }


@router.put("")
def update_settings(patch: SettingsPatch):
    changes: dict[str, Any] = {}
    for key, value in patch.model_dump(exclude_none=True).items():
        # Don't re-apply the masked placeholder for secrets.
        if key in runtime_config.SECRET_KEYS and value == "********":
            continue
        try:
            runtime_config.apply(key, value)
            changes[key] = value
        except ValueError as e:
            raise HTTPException(400, str(e))

    # Rebuild scraper client if provider or credentials changed.
    if any(k in changes for k in ("scraper_provider", "insta_username", "insta_password", "insta_proxy")):
        manager.reset()

    # Reschedule to pick up new cron / enabled.
    from ..scheduler import start_scheduler

    start_scheduler()

    return {"changes": changes, "settings": runtime_config.snapshot()}
