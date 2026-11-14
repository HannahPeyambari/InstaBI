"""Render and deliver a daily report. Never include bot URLs in errors/logs."""
from io import BytesIO
from threading import Lock

import httpx
from matplotlib.figure import Figure
from sqlalchemy import select

from . import models, runtime_config as cfg
from .api.stats import leaderboard
from .database import SessionLocal

_lock = Lock()


def render_report(db):
    # Bucket successful captures into UTC days; retain each account's last
    # capture that day and carry it forward rather than summing partial runs.
    snapshots = db.scalars(select(models.Snapshot).where(
        models.Snapshot.status == "ok"
    ).order_by(models.Snapshot.captured_at, models.Snapshot.id)).all()
    days = {}
    totals = {}
    for snap in snapshots:
        totals[snap.handle_id] = snap.follower_count
        days[snap.captured_at.date()] = sum(totals.values())
    points = list(days.items())[-30:]
    if len(points) < 2:
        raise ValueError("At least two days of successful snapshots are needed for a trend report.")
    fig = Figure(figsize=(12, 12), tight_layout=True)
    followers_ax, gained_ax, text_ax = fig.subplots(3, 1)
    dates, counts = zip(*points)
    followers_ax.plot(dates, counts, color="#7c5cff", marker="o")
    followers_ax.set(title="InstaBI — daily follower trend", ylabel="Total followers")
    gained_ax.plot(dates[1:], [b - a for a, b in zip(counts, counts[1:])], color="#22a555", marker="o")
    gained_ax.set(ylabel="Net change", xlabel="Capture date (UTC)")
    for ax in (followers_ax, gained_ax):
        ax.grid(alpha=.25)
    fig.autofmt_xdate()
    image = BytesIO()
    period = int(cfg.get("telegram_period"))
    lines = [f"InstaBI • {period}-day growth leaderboard", "Trend: last 30 capture days; totals include tracked history."]
    for metric, title in (("gained", "Most followers gained"), ("pct", "Highest percentage growth")):
        rows = leaderboard(period=period, sort=metric, db=db)["entries"]
        if metric == "pct":
            rows = [r for r in rows if r["pct"] is not None]
        lines.append("\n" + title)
        for i, row in enumerate(rows[:5], 1):
            pct = f'{row["pct"]:+.2f}%' if row["pct"] is not None else "N/A"
            lines.append(f'{i}. @{row["username"]}: {row["gained"]:+,} ({pct})')
        if not rows:
            lines.append("Not enough history for this period.")
    lines.append("\nBaselines: last successful capture at or before the selected period; may be older. Only active accounts ranked.")
    text_ax.axis("off")
    text_ax.text(0, 1, "\n".join(lines), va="top", fontsize=9, wrap=True, transform=text_ax.transAxes)
    fig.savefig(image, format="png")
    return image.getvalue(), f"InstaBI daily trend and {period}-day growth leaderboards. Based on stored snapshots; run checks regularly."


def send_report():
    if not _lock.acquire(blocking=False):
        raise ValueError("A Telegram report is already being sent.")
    try:
        token = cfg.get("telegram_bot_token")
        chat = cfg.get("telegram_chat_id")
        if not token or not chat:
            raise ValueError("Save a Telegram bot token and group chat ID first.")
        with SessionLocal() as db:
            image, caption = render_report(db)
        data = {"chat_id": chat, "caption": caption}
        if cfg.get("telegram_thread_id"):
            data["message_thread_id"] = str(cfg.get("telegram_thread_id"))
        # httpx's request logger includes the token-bearing URL; suppress it.
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        try:
            response = httpx.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                                  data=data, files={"photo": ("instabi.png", image, "image/png")}, timeout=45)
            if response.status_code != 200 or not response.json().get("ok"):
                raise ValueError("Telegram rejected the report. Check token, group/topic IDs and photo permissions.")
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError("Telegram delivery failed. Check credentials, permissions and internet connectivity.") from None
    finally:
        _lock.release()
