"""ORM models: handles, snapshots (time-series stats), run logs, settings."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Handle(Base):
    """A tracked Instagram account (by handle/username)."""

    __tablename__ = "handles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_checked_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_snapshot_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    snapshots: Mapped[list["Snapshot"]] = relationship(
        back_populates="handle",
        cascade="all, delete-orphan",
        order_by="Snapshot.captured_at.desc()",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "notes": self.notes,
            "active": self.active,
            "created_at": iso(self.created_at),
            "last_checked_at": iso(self.last_checked_at),
            "last_status": self.last_status,
            "last_error": self.last_error,
            "last_snapshot_id": self.last_snapshot_id,
        }


class Snapshot(Base):
    """A single point-in-time capture of a handle's stats."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    handle_id: Mapped[int] = mapped_column(
        ForeignKey("handles.id", ondelete="CASCADE"), index=True
    )
    captured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    username: Mapped[str] = mapped_column(String(64), index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    media_count: Mapped[int] = mapped_column(Integer, default=0)

    recent_likes: Mapped[int] = mapped_column(Integer, default=0)
    recent_comments: Mapped[int] = mapped_column(Integer, default=0)
    recent_views: Mapped[int] = mapped_column(Integer, default=0)
    recent_posts: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)

    top_post: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    biography: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(24), default="ok")  # ok | error
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    raw: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    handle: Mapped["Handle"] = relationship(back_populates="snapshots")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "handle_id": self.handle_id,
            "captured_at": iso(self.captured_at),
            "username": self.username,
            "full_name": self.full_name,
            "is_private": self.is_private,
            "is_verified": self.is_verified,
            "follower_count": self.follower_count,
            "following_count": self.following_count,
            "media_count": self.media_count,
            "recent_likes": self.recent_likes,
            "recent_comments": self.recent_comments,
            "recent_views": self.recent_views,
            "recent_posts": self.recent_posts,
            "engagement_rate": round(self.engagement_rate, 4),
            "top_post": self.top_post,
            "avatar_url": self.avatar_url,
            "biography": self.biography,
            "status": self.status,
            "error": self.error,
            "provider": self.provider,
        }


class RunLog(Base):
    """A single scheduler/manual run: how many handles, successes, failures."""

    __tablename__ = "run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trigger: Mapped[str] = mapped_column(String(24), default="schedule")  # schedule | manual
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    handles_total: Mapped[int] = mapped_column(Integer, default=0)
    ok_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "started_at": iso(self.started_at),
            "finished_at": iso(self.finished_at),
            "trigger": self.trigger,
            "provider": self.provider,
            "handles_total": self.handles_total,
            "ok_count": self.ok_count,
            "failed_count": self.failed_count,
            "detail": self.detail,
        }


class Setting(Base):
    """Simple key/value store for runtime settings overridable from the panel."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)

    def to_dict(self) -> dict:
        return {"key": self.key, "value": self.value}


def iso(dt_value: Optional[dt.datetime]) -> Optional[str]:
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=dt.UTC)
    return dt_value.astimezone(dt.UTC).isoformat()
