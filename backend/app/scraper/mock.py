"""Deterministic mock provider.

Produces stable, realistic-looking stats for any handle so the whole system
(scheduler, DB, charts, admin panel) can be exercised without Instagram
credentials. A small random walk makes the time series feel alive.
"""
from __future__ import annotations

import hashlib
import random

from .base import ProfileStats

_VERBS = ["Sharing", "Posting", "Creating", "Launching", "Teaching", "Building"]


def _seed(username: str) -> int:
    return int(hashlib.sha256(username.lower().encode()).hexdigest()[:8], 16)


class MockClient:
    name = "mock"

    def __init__(self, recent_media_count: int = 12):
        self.recent_media_count = recent_media_count

    def get_stats(self, username: str) -> ProfileStats:
        username = username.lstrip("@")
        rng = random.Random(_seed(username))

        # Always succeeds in mock mode — every handle returns realistic data so
        # the demo never shows spurious "not found" failures.
        base_followers = rng.randint(2_000, 8_000_000)
        # Small per-call drift so each daily run differs slightly.
        drift = rng.randint(-3, 6)
        followers = max(0, base_followers + drift)
        following = rng.randint(80, 2_500)
        media = rng.randint(20, 2_500)
        is_private = rng.random() < 0.08
        is_verified = followers > 500_000 and rng.random() < 0.6

        recent_posts = min(self.recent_media_count, media) if not is_private else 0

        # Per-post engagement: ~1%-6% of followers, shrinking for big accounts.
        per_post_er = rng.uniform(0.01, 0.06) / (1 + followers / 1_000_000)
        likes = int(followers * per_post_er * recent_posts) if recent_posts else 0
        comments = int(likes * rng.uniform(0.04, 0.14)) if likes else 0
        views = int(likes * rng.uniform(3, 9)) if recent_posts else 0
        # engagement_rate = average per-post (likes+comments)/followers, in %.
        er = ((likes + comments) / (followers * recent_posts)) * 100 if followers and recent_posts else 0.0
        # (er is already in percent)

        top = None
        if recent_posts:
            top_likes = int(likes / recent_posts * rng.uniform(1.5, 4.0))
            top = {
                "shortcode": hashlib.md5(username.encode()).hexdigest()[:9],
                "pk": rng.randint(10**9, 10**12),
                "like_count": top_likes,
                "comment_count": int(top_likes * 0.08),
                "view_count": int(top_likes * rng.uniform(4, 10)),
                "media_type": rng.choice([1, 2, 2, 8]),  # 2 = carousel, 8 = reel
                "thumbnail_url": f"https://picsum.photos/seed/{username}/400/400",
            }

        return ProfileStats(
            username=username,
            full_name=f"{username.replace('_', ' ').title()} {rng.choice(_VERBS)}",
            is_private=is_private,
            is_verified=is_verified,
            follower_count=followers,
            following_count=following,
            media_count=media,
            recent_likes=likes,
            recent_comments=comments,
            recent_views=views,
            recent_posts=recent_posts,
            engagement_rate=round(er, 3),
            top_post=top,
            avatar_url=f"https://picsum.photos/seed/{username}-av/200/200",
            biography=f"Mock profile for {username}. Connected via InstaBI demo mode.",
            provider=self.name,
        )

    def healthcheck(self) -> tuple[bool, str]:
        return True, "mock provider ready (no Instagram credentials required)"
