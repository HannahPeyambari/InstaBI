"""Scraper provider interface and shared data structures."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, Protocol


class ScraperError(Exception):
    """Raised when a profile cannot be scraped.

    ``kind`` is a short machine label used for status badges in the UI:
    ``not_found``, ``private``, ``rate_limited``, ``login_required``,
    ``network``, ``other``.
    """

    def __init__(self, message: str, kind: str = "other"):
        super().__init__(message)
        self.kind = kind


@dataclass
class TopPost:
    shortcode: str
    pk: Optional[int]
    like_count: int
    comment_count: int
    view_count: int
    media_type: int
    thumbnail_url: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProfileStats:
    username: str
    full_name: Optional[str] = None
    is_private: bool = False
    is_verified: bool = False
    follower_count: int = 0
    following_count: int = 0
    media_count: int = 0
    # Engagement over the most recent ``recent_media_count`` posts.
    recent_likes: int = 0
    recent_comments: int = 0
    recent_views: int = 0
    recent_posts: int = 0
    engagement_rate: float = 0.0  # % of (likes+comments) per follower
    top_post: Optional[dict] = None
    avatar_url: Optional[str] = None
    biography: Optional[str] = None
    provider: str = "mock"

    def to_dict(self) -> dict:
        return asdict(self)


class ScraperClient(Protocol):
    """Any scraper provider must expose ``get_stats(username)``."""

    name: str

    def get_stats(self, username: str) -> ProfileStats: ...

    def healthcheck(self) -> tuple[bool, str]: ...
