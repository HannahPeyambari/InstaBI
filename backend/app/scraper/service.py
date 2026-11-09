"""Scraping orchestration: run checks over handles and persist snapshots."""
from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from .. import runtime_config
from .base import ScraperError, ScraperClient
from .manager import manager

log = logging.getLogger(__name__)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def create_snapshot(db: Session, handle: models.Handle, stats, status: str = "ok", error: Optional[str] = None) -> models.Snapshot:
    """Persist a ProfileStats object as a Snapshot row and update the handle."""
    snap = models.Snapshot(
        handle_id=handle.id,
        username=handle.username,
        captured_at=_now(),
        full_name=getattr(stats, "full_name", None) if status == "ok" else None,
        is_private=bool(getattr(stats, "is_private", False)) if status == "ok" else False,
        is_verified=bool(getattr(stats, "is_verified", False)) if status == "ok" else False,
        follower_count=int(getattr(stats, "follower_count", 0) or 0),
        following_count=int(getattr(stats, "following_count", 0) or 0),
        media_count=int(getattr(stats, "media_count", 0) or 0),
        recent_likes=int(getattr(stats, "recent_likes", 0) or 0),
        recent_comments=int(getattr(stats, "recent_comments", 0) or 0),
        recent_views=int(getattr(stats, "recent_views", 0) or 0),
        recent_posts=int(getattr(stats, "recent_posts", 0) or 0),
        engagement_rate=float(getattr(stats, "engagement_rate", 0.0) or 0.0),
        top_post=getattr(stats, "top_post", None),
        avatar_url=getattr(stats, "avatar_url", None),
        biography=getattr(stats, "biography", None),
        status=status,
        error=error,
        provider=getattr(stats, "provider", None),
    )
    db.add(snap)
    db.flush()  # get snap.id

    handle.last_checked_at = snap.captured_at
    handle.last_status = status
    handle.last_error = error
    handle.last_snapshot_id = snap.id
    db.flush()
    return snap


def run_checks(
    db: Session,
    handles: Optional[Iterable[models.Handle]] = None,
    trigger: str = "manual",
    client: Optional[ScraperClient] = None,
) -> models.RunLog:
    """Scrape a set of handles and write snapshots + a RunLog.

    ``handles`` defaults to all active handles.
    """
    client = client or manager.get()

    if handles is None:
        handles = db.scalars(select(models.Handle).where(models.Handle.active.is_(True))).all()
    handles = list(handles)

    run = models.RunLog(
        started_at=_now(),
        trigger=trigger,
        provider=client.name,
        handles_total=len(handles),
        ok_count=0,
        failed_count=0,
    )
    db.add(run)
    db.flush()

    errors: list[str] = []
    for i, handle in enumerate(handles):
        try:
            stats = client.get_stats(handle.username)
            create_snapshot(db, handle, stats, status="ok", error=None)
            run.ok_count += 1
        except ScraperError as e:
            create_snapshot(db, handle, None, status="error", error=f"[{e.kind}] {e}")
            run.failed_count += 1
            errors.append(f"{handle.username}: {e}")
        except Exception as e:  # noqa: BLE001
            log.exception("Unexpected error scraping %s", handle.username)
            create_snapshot(db, handle, None, status="error", error=str(e))
            run.failed_count += 1
            errors.append(f"{handle.username}: {e}")
        db.commit()

        # Gentle pacing between handles.
        if runtime_config.get("per_handle_delay") > 0 and i < len(handles) - 1:
            time.sleep(float(runtime_config.get("per_handle_delay")))

    run.finished_at = _now()
    run.detail = "; ".join(errors) if errors else None
    db.commit()
    db.refresh(run)
    log.info(
        "Run complete: %s/%s ok (trigger=%s)", run.ok_count, run.handles_total, trigger
    )
    return run
