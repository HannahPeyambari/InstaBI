"""Periodic scheduler: fires a scrape run on the configured cron schedule."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import SessionLocal
from .scraper.manager import manager
from .scraper.service import run_checks

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def _job():
    """Run scheduled checks for all active handles."""
    db = SessionLocal()
    try:
        run_checks(db, trigger="schedule")
    except Exception:  # noqa: BLE001
        log.exception("Scheduled run failed")
    finally:
        db.close()


def start_scheduler() -> None:
    from . import runtime_config

    scheduler.remove_all_jobs()
    if runtime_config.get("telegram_enabled"):
        scheduler.add_job(_telegram_job, "interval", hours=24, id="telegram_report",
                          replace_existing=True, coalesce=True, max_instances=1,
                          misfire_grace_time=3600)
        if not scheduler.running:
            scheduler.start()
    if not runtime_config.get("schedule_enabled"):
        log.info("Scheduler disabled by config")
        return
    cron = str(runtime_config.get("schedule_cron"))
    try:
        trigger = CronTrigger.from_crontab(cron, timezone="UTC")
    except ValueError as e:
        log.warning("Invalid schedule_cron %r, falling back to daily 03:00: %s", cron, e)
        trigger = CronTrigger(hour=3, minute=0, timezone="UTC")

    scheduler.add_job(
        _job,
        trigger=trigger,
        id="periodic_check",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    if not scheduler.running:
        scheduler.start()
    log.info("Scheduler started; next run from cron %r", cron)


def get_status() -> dict:
    from . import runtime_config

    jobs = []
    try:
        for job in sorted(scheduler.get_jobs(), key=lambda j: j.id != "periodic_check"):
            jobs.append(
                {
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
            )
    except Exception:  # noqa: BLE001
        pass
    return {
        "running": scheduler.running,
        "enabled": bool(runtime_config.get("schedule_enabled")),
        "cron": str(runtime_config.get("schedule_cron")),
        "provider": str(runtime_config.get("scraper_provider")),
        "jobs": jobs,
    }


def _telegram_job():
    from .telegram_report import send_report
    try:
        send_report()
    except Exception:
        # Do not log exceptions that might contain token-bearing URLs.
        log.warning("Telegram report failed; check configuration, history and connectivity.")
