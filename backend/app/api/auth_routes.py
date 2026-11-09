"""Auth endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..auth import check_credentials, issue_token
from ..config import settings
from ..schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response):
    if not check_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token, expires_in = issue_token(payload.username)
    response.set_cookie(
        "instabi_token",
        token,
        max_age=expires_in,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
    )
    return LoginResponse(token=token, expires_in=expires_in, username=payload.username)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("instabi_token")
    return {"ok": True}


@router.get("/me")
def me():
    return {"username": settings.admin_username, "provider": settings.scraper_provider}
