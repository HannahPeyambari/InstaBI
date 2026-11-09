"""Run log endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from .deps import require_auth

router = APIRouter(prefix="/api/runs", tags=["runs"], dependencies=[Depends(require_auth)])


@router.get("")
def list_runs(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    runs = db.scalars(
        select(models.RunLog).order_by(models.RunLog.started_at.desc()).limit(limit)
    ).all()
    return [r.to_dict() for r in runs]
