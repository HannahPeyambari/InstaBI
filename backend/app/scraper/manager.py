"""Build and hold the active scraper provider."""
from __future__ import annotations

import logging
from typing import Optional

from .. import runtime_config
from .base import ScraperClient
from .instagrapi_client import InstagrapiClient
from .mock import MockClient

log = logging.getLogger(__name__)


class ScraperManager:
    """Lazily constructs the configured provider and keeps a single instance."""

    def __init__(self) -> None:
        self._client: Optional[ScraperClient] = None
        self._provider: Optional[str] = None
        self._built_sig: Optional[tuple] = None

    def provider_name(self) -> str:
        return runtime_config.get("scraper_provider")

    def get(self) -> ScraperClient:
        provider = self.provider_name().lower()
        # Rebuild if the provider or credentials changed since last build.
        if (
            self._client is not None
            and self._provider == provider
            and self._built_sig == self._cred_sig()
        ):
            return self._client

        if provider == "instagrapi":
            client: ScraperClient = InstagrapiClient(
                username=runtime_config.get("insta_username"),
                password=runtime_config.get("insta_password"),
                session_file=settings_session_file(),
                proxy=runtime_config.get("insta_proxy") or "",
                recent_media_count=int(runtime_config.get("recent_media_count")),
            )
        elif provider == "mock":
            client = MockClient(recent_media_count=int(runtime_config.get("recent_media_count")))
        else:
            raise ValueError(f"Unknown scraper provider: {provider}")

        self._client = client
        self._provider = provider
        self._built_sig = self._cred_sig()
        log.info("Scraper provider initialized: %s", provider)
        return client

    def reset(self) -> None:
        """Drop the cached client (e.g. after credentials change)."""
        self._client = None
        self._provider = None
        self._built_sig = None

    def _cred_sig(self) -> tuple:
        return (
            runtime_config.get("insta_username"),
            runtime_config.get("insta_password"),
            runtime_config.get("insta_proxy"),
        )

    def healthcheck(self) -> tuple[bool, str]:
        try:
            return self.get().healthcheck()
        except Exception as e:  # noqa: BLE001
            return False, str(e)


def settings_session_file() -> str:
    from ..config import settings

    return settings.session_file


manager = ScraperManager()

