"""Handle management: CRUD, bulk import, manual checks."""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..schemas import HandleBulkCreate, HandleCreate, HandleOut, HandleUpdate
from ..scraper.manager import manager
from ..scraper.service import run_checks
from .deps import require_auth

router = APIRouter(prefix="/api/handles", tags=["handles"], dependencies=[Depends(require_auth)])

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")


def _normalize(raw: str) -> Optional[str]:
    raw = raw.strip().lstrip("@")
    if not _USERNAME_RE.match(raw):
        return None
    return raw.lower()


def _parse_usernames(text: str) -> list[str]:
    # Split on commas, whitespace, semicolons, or newlines.
    parts = re.split(r"[\s,;]+", text.strip())
    seen, out = set(), []
    for p in parts:
        if not p:
            continue
        u = _normalize(p)
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


@router.get("", response_model=list[HandleOut])
def list_handles(db: Session = Depends(get_db)):
    return [h.to_dict() for h in db.scalars(select(models.Handle).order_by(models.Handle.created_at)).all()]


@router.get("/failed", response_model=list[HandleOut])
def list_failed(db: Session = Depends(get_db)):
    """Return handles whose most recent check failed (with error details)."""
    handles = db.scalars(
        select(models.Handle)
        .where(models.Handle.last_status == "error")
        .order_by(models.Handle.username)
    ).all()
    return [h.to_dict() for h in handles]


@router.post("", response_model=HandleOut, status_code=201)
def create_handle(payload: HandleCreate, db: Session = Depends(get_db)):
    username = _normalize(payload.username)
    if not username:
        raise HTTPException(400, "Invalid username")
    if db.scalar(select(models.Handle).where(models.Handle.username == username)):
        raise HTTPException(409, "Handle already tracked")
    h = models.Handle(
        username=username,
        display_name=payload.display_name,
        notes=payload.notes,
        active=payload.active,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return h.to_dict()


@router.post("/bulk", response_model=dict, status_code=201)
def bulk_add(payload: HandleBulkCreate, db: Session = Depends(get_db)):
    usernames: list[str] = []
    if payload.handles:
        for raw in payload.handles:
            u = _normalize(raw)
            if u:
                usernames.append(u)
    if payload.text:
        usernames.extend(_parse_usernames(payload.text))
    # dedupe preserving order
    seen, uniq = set(), []
    for u in usernames:
        if u not in seen:
            seen.add(u)
            uniq.append(u)

    added, skipped = 0, 0
    for u in uniq:
        if db.scalar(select(models.Handle).where(models.Handle.username == u)):
            skipped += 1
            continue
        db.add(models.Handle(username=u, display_name=payload.display_name, notes=payload.notes, active=payload.active))
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped, "total": len(uniq)}


@router.put("/{handle_id}", response_model=HandleOut)
def update_handle(handle_id: int, payload: HandleUpdate, db: Session = Depends(get_db)):
    h = db.get(models.Handle, handle_id)
    if not h:
        raise HTTPException(404, "Handle not found")
    for field in ("display_name", "notes", "active"):
        val = getattr(payload, field)
        if val is not None:
            setattr(h, field, val)
    db.commit()
    db.refresh(h)
    return h.to_dict()


@router.delete("/{handle_id}", status_code=204)
def delete_handle(handle_id: int, db: Session = Depends(get_db)):
    h = db.get(models.Handle, handle_id)
    if not h:
        raise HTTPException(404, "Handle not found")
    db.delete(h)
    db.commit()


@router.post("/{handle_id}/check", response_model=dict)
def check_handle(handle_id: int, db: Session = Depends(get_db)):
    h = db.get(models.Handle, handle_id)
    if not h:
        raise HTTPException(404, "Handle not found")
    run = run_checks(db, handles=[h], trigger="manual")
    return {"run": run.to_dict(), "handle": h.to_dict()}


@router.post("/check-all", response_model=dict)
def check_all(db: Session = Depends(get_db)):
    handles = db.scalars(select(models.Handle).where(models.Handle.active.is_(True))).all()
    run = run_checks(db, handles=handles, trigger="manual")
    return {"run": run.to_dict()}


@router.post("/delete-failed", response_model=dict)
def delete_failed(db: Session = Depends(get_db)):
    """Remove every tracked handle whose most recent check failed.

    Covers 'not found' accounts and any other scraping errors. The handle and
    all of its snapshot history are deleted.
    """
    failed = db.scalars(select(models.Handle).where(models.Handle.last_status == "error")).all()
    usernames = [h.username for h in failed]
    for h in failed:
        db.delete(h)
    db.commit()
    return {"deleted": len(usernames), "usernames": usernames}


@router.get("/provider/health", response_model=dict)
def provider_health():
    ok, message = manager.healthcheck()
    return {"ok": ok, "message": message, "provider": manager.provider_name()}
