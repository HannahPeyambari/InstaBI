"""Application configuration.

Settings are read from environment variables and/or a ``backend/.env`` file.
Nothing sensitive is ever committed: credentials live only in the environment
(or a git-ignored ``.env``). The admin panel password is stored hashed.
"""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
PROJECT_ROOT = BASE_DIR.parent                              # repo root
DATA_DIR = Path(os.environ.get("INSTABI_DATA_DIR", BASE_DIR / "data"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INSTABI_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "InstaBI"
    debug: bool = False
    # How the built React frontend is served. `auto` uses frontend/dist if
    # present, otherwise a minimal API-only fallback page is served.
    serve_frontend: bool = True

    # --- Database ---
    db_path: str = str(DATA_DIR / "instabi.db")

    # --- Auth ---
    # If empty, a random admin password is generated on first boot and written
    # to backend/data/admin_password.txt (git-ignored).
    admin_username: str = "admin"
    admin_password: str = ""
    admin_token_secret: str = ""
    session_ttl_hours: int = 72

    # --- Scraper ---
    # `mock` = deterministic demo data (no Instagram access). `instagrapi` =
    # real scraping via the unofficial API (needs Instagram credentials).
    scraper_provider: str = "mock"
    # Instagram login credentials. Leave blank for mock mode.
    insta_username: str = ""
    insta_password: str = ""
    insta_proxy: str = ""
    # Session pickle path for instagrapi (persists login across restarts).
    session_file: str = str(DATA_DIR / "instagrapi_session.pkl")

    # --- Scheduler ---
    # Cron expression (5 fields) OR a plain day-interval in hours.
    schedule_cron: str = "0 3 * * *"          # default: 03:00 daily
    schedule_enabled: bool = True
    # Per-handle delay between checks (seconds) to avoid rate limits.
    per_handle_delay: float = 2.0
    # Max recent media to pull for engagement metrics.
    recent_media_count: int = 12

    @property
    def schedule_interval_hours(self) -> int:
        """Best-effort human-readable interval for the UI (used if cron is
        a simple 'every N hours' expression)."""
        return 24

    def ensure_dirs(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def resolved_admin_password(self) -> str:
        if self.admin_password:
            return self.admin_password
        pw_file = DATA_DIR / "admin_password.txt"
        if pw_file.exists():
            return pw_file.read_text().strip()
        pw = "admin-" + secrets.token_urlsafe(12)
        pw_file.write_text(pw)
        os.chmod(pw_file, 0o600)
        return pw

    def resolved_token_secret(self) -> str:
        if self.admin_token_secret:
            return self.admin_token_secret
        sf = DATA_DIR / "token_secret.key"
        if sf.exists():
            return sf.read_text().strip()
        s = secrets.token_urlsafe(32)
        sf.write_text(s)
        os.chmod(sf, 0o600)
        return s


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s


settings = get_settings()
