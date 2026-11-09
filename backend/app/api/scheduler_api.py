"""Scheduler control endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..scheduler import get_status, start_scheduler
from ..scraper.service import run_checks
from .deps import require_auth

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"], dependencies=[Depends(require_auth)])


@router.get("")
def status():
    return get_status()


@router.post("/run")
def run_now(db: Session = Depends(get_db)):
    run = run_checks(db, trigger="manual")
    return {"run": run.to_dict()}


@router.post("/reschedule")
def reschedule():
    start_scheduler()
    return get_status()
