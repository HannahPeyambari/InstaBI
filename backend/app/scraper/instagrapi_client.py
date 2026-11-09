"""Real Instagram provider backed by the unofficial ``instagrapi`` API.

Requires Instagram login credentials (username/password) OR a persisted
session file. Handles login, session caching, error classification, and
engagement metrics from recent media.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from .base import ProfileStats, ScraperError, TopPost

log = logging.getLogger(__name__)


class InstagrapiClient:
    name = "instagrapi"

    def __init__(
        self,
        username: str,
        password: str,
        session_file: str,
        proxy: str = "",
        recent_media_count: int = 12,
    ):
        self.username = username
        self.password = password
        self.session_file = Path(session_file)
        self.proxy = proxy or None
        self.recent_media_count = recent_media_count
        self._client = None

    # ---- lifecycle ----
    def _new_client(self):
        # Imported lazily so the rest of the app works even if instagrapi
        # is not installed (e.g. mock-only deployment).
        from instagrapi import Client

        return Client(proxy=self.proxy) if self.proxy else Client()

    def _load_session(self):
        if not self.session_file.exists():
            return None
        try:
            c = self._new_client()
            c.load_settings(str(self.session_file))
            return c
        except Exception as e:  # noqa: BLE001
            log.warning("Could not restore Instagram session: %s", e)
            return None

    def _save_session(self, client) -> None:
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            client.dump_settings(str(self.session_file))
            os.chmod(self.session_file, 0o600)
        except Exception as e:  # noqa: BLE001
            log.warning("Could not persist Instagram session: %s", e)

    def login(self):
        if self._client is not None:
            return self._client
        client = self._load_session()
        if client is None:
            if not self.username or not self.password:
                raise ScraperError(
                    "No Instagram credentials configured (set INSTABI_INSTA_USERNAME / "
                    "INSTABI_INSTA_PASSWORD, or switch provider to 'mock').",
                    kind="login_required",
                )
            client = self._new_client()
            try:
                client.login(self.username, self.password)
            except Exception as e:  # noqa: BLE001
                raise ScraperError(
                    f"Instagram login failed: {e}", kind=self._classify(e)
                ) from e
            self._save_session(client)
        self._client = client
        return client

    # ---- stats ----
    def get_stats(self, username: str) -> ProfileStats:
        username = username.lstrip("@")
        client = self.login()
        try:
            user = client.user_info_by_username(username)
        except Exception as e:  # noqa: BLE001
            raise ScraperError(str(e), kind=self._classify(e)) from e

        followers = int(user.follower_count or 0)
        following = int(user.following_count or 0)
        media_count = int(user.media_count or 0)

        stats = ProfileStats(
            username=username,
            full_name=user.full_name,
            is_private=bool(user.is_private),
            is_verified=bool(user.is_verified),
            follower_count=followers,
            following_count=following,
            media_count=media_count,
            avatar_url=user.profile_pic_url_hd or user.profile_pic_url,
            biography=user.biography,
            provider=self.name,
        )

        # Engagement from the most recent posts (skip for private accounts).
        if not user.is_private and followers:
            self._enrich_engagement(client, user.pk, stats)

        return stats

    def _enrich_engagement(self, client, user_pk, stats: ProfileStats) -> None:
        try:
            medias = client.user_medias(user_pk, amount=self.recent_media_count, sleep=0)
        except Exception as e:  # noqa: BLE001
            log.debug("user_medias failed for %s: %s", user_pk, e)
            return

        if not medias:
            return

        recent = list(medias)[: self.recent_media_count]
        likes = sum(m.like_count or 0 for m in recent)
        comments = sum(m.comment_count or 0 for m in recent)
        views = sum(m.view_count or 0 for m in recent if m.view_count)

        stats.recent_likes = likes
        stats.recent_comments = comments
        stats.recent_views = views
        stats.recent_posts = len(recent)
        stats.engagement_rate = (
            (likes + comments) / (stats.follower_count * len(recent)) * 100
            if stats.follower_count and recent
            else 0.0
        )

        # Top post by likes.
        try:
            top = max(recent, key=lambda m: m.like_count or 0)
            stats.top_post = TopPost(
                shortcode=top.code,
                pk=top.pk,
                like_count=top.like_count or 0,
                comment_count=top.comment_count or 0,
                view_count=top.view_count or 0,
                media_type=top.media_type,
                thumbnail_url=self._thumb(top),
            ).to_dict()
        except Exception:  # noqa: BLE001
            stats.top_post = None

    def _thumb(self, media) -> Optional[str]:
        try:
            candidates = media.image_versions2.candidates  # type: ignore[attr-defined]
            if candidates:
                return candidates[0].url
        except Exception:  # noqa: BLE001
            pass
        return media.thumbnail_url

    def healthcheck(self) -> tuple[bool, str]:
        if not self.username or not self.password:
            return False, "No Instagram credentials configured"
        try:
            self.login()
            return True, "Connected to Instagram via instagrapi"
        except ScraperError as e:
            return False, str(e)
        except Exception as e:  # noqa: BLE001
            return False, f"Healthcheck failed: {e}"

    # ---- error classification ----
    @staticmethod
    def _classify(exc: Exception) -> str:
        try:
            from instagrapi.exceptions import (
                AccountSuspended,
                BadCredentials,
                BadPassword,
                ChallengeRequired,
                CaptchaChallengeRequired,
                ClientLoginRequired,
                ClientRequestTimeout,
                ClientThrottledError,
                LoginRequired,
                PrivateAccount,
                PrivateError,
                ProxyAddressIsBlocked,
                RateLimitError,
                SentryBlock,
                TwoFactorRequired,
                UserNotFound,
            )
        except Exception:  # noqa: BLE001  (instagrapi missing)
            return "other"

        mapping = [
            (UserNotFound, "not_found"),
            (PrivateError, "private"),
            (PrivateAccount, "private"),
            (RateLimitError, "rate_limited"),
            (ClientThrottledError, "rate_limited"),
            (ClientRequestTimeout, "rate_limited"),
            (LoginRequired, "login_required"),
            (ClientLoginRequired, "login_required"),
            (BadCredentials, "login_required"),
            (BadPassword, "login_required"),
            (TwoFactorRequired, "login_required"),
            (ChallengeRequired, "login_required"),
            (CaptchaChallengeRequired, "login_required"),
            (ProxyAddressIsBlocked, "blocked"),
            (SentryBlock, "blocked"),
            (AccountSuspended, "blocked"),
        ]
        for cls, kind in mapping:
            if isinstance(exc, cls):
                return kind
        return "network" if isinstance(exc, (ConnectionError, TimeoutError)) else "other"
