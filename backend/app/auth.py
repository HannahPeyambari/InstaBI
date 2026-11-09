"""Lightweight stateless auth: HMAC-signed bearer tokens.

No external JWT dependency. Tokens carry ``username|expiry_epoch`` and an HMAC
signature, base64-url encoded. Verification is constant-time.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from .config import settings


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def issue_token(username: str) -> tuple[str, int]:
    expires_in = settings.session_ttl_hours * 3600
    payload = {"u": username, "exp": int(time.time()) + expires_in}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(settings.resolved_token_secret().encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", expires_in


def verify_token(token: str) -> str | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = _b64(hmac.new(settings.resolved_token_secret().encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(_unb64(body))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < time.time():
        return None
    return payload.get("u")


def check_credentials(username: str, password: str) -> bool:
    expected_user = settings.admin_username
    expected_pw = settings.resolved_admin_password()
    return hmac.compare_digest(username, expected_user) and hmac.compare_digest(password, expected_pw)
