"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int  # seconds
    username: str


# ---- Handles ----
class HandleCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    display_name: Optional[str] = None
    notes: Optional[str] = None
    active: bool = True


class HandleBulkCreate(BaseModel):
    # Comma/newline separated list, or an explicit list of usernames.
    handles: Optional[list[str]] = None
    text: Optional[str] = None
    display_name: Optional[str] = None
    notes: Optional[str] = None
    active: bool = True


class HandleUpdate(BaseModel):
    display_name: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class HandleOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    notes: Optional[str]
    active: bool
    created_at: Optional[str]
    last_checked_at: Optional[str]
    last_status: Optional[str]
    last_error: Optional[str]
    last_snapshot_id: Optional[int]


# ---- Snapshots / stats ----
class SnapshotOut(BaseModel):
    id: int
    handle_id: int
    captured_at: Optional[str]
    username: str
    full_name: Optional[str]
    is_private: bool
    is_verified: bool
    follower_count: int
    following_count: int
    media_count: int
    recent_likes: int
    recent_comments: int
    recent_views: int
    recent_posts: int
    engagement_rate: float
    top_post: Optional[dict]
    avatar_url: Optional[str]
    biography: Optional[str]
    status: str
    error: Optional[str]
    provider: Optional[str]


class OverviewOut(BaseModel):
    total_handles: int
    active_handles: int
    last_run: Optional[dict]
    followers_total: int
    followers_change_24h: int
    top_gainers: list[dict]
    recent_runs: list[dict]
    series: list[dict]  # {ts, followers}
