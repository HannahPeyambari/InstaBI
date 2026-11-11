"""Stats / analytics endpoints: overview, snapshots, trends."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..schemas import SnapshotOut
from .deps import require_auth

router = APIRouter(prefix="/api", tags=["stats"], dependencies=[Depends(require_auth)])


def _latest_snapshots(db: Session) -> dict[int, models.Snapshot]:
    """Return the most recent snapshot for each handle."""
    snaps = db.scalars(
        select(models.Snapshot).order_by(models.Snapshot.captured_at.desc())
    ).all()
    latest: dict[int, models.Snapshot] = {}
    for s in snaps:
        if s.handle_id not in latest:
            latest[s.handle_id] = s
    return latest


def _previous_snapshot(db: Session, handle_id: int, before) -> Optional[models.Snapshot]:
    return db.scalar(
        select(models.Snapshot)
        .where(models.Snapshot.handle_id == handle_id, models.Snapshot.captured_at < before)
        .order_by(models.Snapshot.captured_at.desc())
        .limit(1)
    )


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    handles = db.scalars(select(models.Handle)).all()
    active = [h for h in handles if h.active]
    latest = _latest_snapshots(db)

    followers_total = sum(s.follower_count for s in latest.values() if s.status == "ok")

    # 24h change: compare latest vs previous snapshot per handle.
    changes: list[tuple[str, int, int]] = []
    for h in active:
        snap = latest.get(h.id)
        if not snap or snap.status != "ok":
            continue
        prev = _previous_snapshot(db, h.id, snap.captured_at)
        if prev and prev.status == "ok":
            change = snap.follower_count - prev.follower_count
            # Only count if the previous capture is within ~24h of latest.
            if (snap.captured_at - prev.captured_at) <= timedelta(hours=26):
                changes.append((h.username, change, snap.follower_count))
    followers_change_24h = sum(c for _, c, _ in changes)
    top_gainers = sorted(changes, key=lambda x: x[1], reverse=True)[:5]

    # Last run log.
    last_run = db.scalar(select(models.RunLog).order_by(models.RunLog.started_at.desc()).limit(1))

    # Recent runs.
    recent_runs = [
        r.to_dict()
        for r in db.scalars(select(models.RunLog).order_by(models.RunLog.started_at.desc()).limit(8)).all()
    ]

    # Followers trend across runs (sum of follower_count captured per run).
    runs = db.scalars(select(models.RunLog).order_by(models.RunLog.started_at.asc())).all()
    series: list[dict] = []
    snaps = db.scalars(select(models.Snapshot)).all()
    by_time = defaultdict(int)
    for s in snaps:
        if s.status == "ok":
            by_time[s.captured_at.replace(tzinfo=None)] += s.follower_count
    for r in runs[-30:]:
        t = r.started_at.replace(tzinfo=None)
        # Total followers among snapshots captured at/after this run start,
        # deduplicated to the latest within a short window of the run.
        window = [dt for dt in by_time if dt >= t - timedelta(seconds=5)]
        if window:
            latest_t = max(window)
            series.append({"ts": latest_t.isoformat(), "followers": by_time[latest_t]})

    return {
        "total_handles": len(handles),
        "active_handles": len(active),
        "last_run": last_run.to_dict() if last_run else None,
        "followers_total": followers_total,
        "followers_change_24h": followers_change_24h,
        "top_gainers": [{"username": u, "change": c, "followers": f} for u, c, f in top_gainers],
        "recent_runs": recent_runs,
        "series": series,
    }


@router.get("/handles/{handle_id}/snapshots", response_model=list[SnapshotOut])
def handle_snapshots(handle_id: int, db: Session = Depends(get_db)):
    h = db.get(models.Handle, handle_id)
    if not h:
        raise HTTPException(404, "Handle not found")
    snaps = db.scalars(
        select(models.Snapshot)
        .where(models.Snapshot.handle_id == handle_id)
        .order_by(models.Snapshot.captured_at.asc())
    ).all()
    return [s.to_dict() for s in snaps]


@router.get("/snapshots", response_model=list[SnapshotOut])
def all_snapshots(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=5000),
    handle_id: Optional[int] = None,
):
    stmt = select(models.Snapshot).order_by(models.Snapshot.captured_at.desc()).limit(limit)
    if handle_id:
        stmt = (
            select(models.Snapshot)
            .where(models.Snapshot.handle_id == handle_id)
            .order_by(models.Snapshot.captured_at.desc())
            .limit(limit)
        )
    return [s.to_dict() for s in db.scalars(stmt).all()]


@router.get("/compare")
def compare(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100)):
    """Latest stats for every tracked handle (dashboard table)."""
    handles = db.scalars(select(models.Handle).order_by(models.Handle.username)).all()
    latest = _latest_snapshots(db)
    out = []
    for h in handles:
        snap = latest.get(h.id)
        out.append(
            {
                "handle": h.to_dict(),
                "snapshot": snap.to_dict() if snap else None,
            }
        )
    return out[:limit]
