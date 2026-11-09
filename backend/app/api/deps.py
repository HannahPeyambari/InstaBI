"""Shared FastAPI dependencies (DB session + auth)."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import verify_token
from ..database import get_db


async def require_auth(request: Request, db: Session = Depends(get_db)) -> str:
    auth = request.headers.get("Authorization", "")
    token: Optional[str] = None
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        # Also accept a cookie for browser convenience.
        token = request.cookies.get("instabi_token")
    username = verify_token(token) if token else None
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return username
