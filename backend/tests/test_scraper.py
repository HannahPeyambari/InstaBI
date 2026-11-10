"""Tests for the scraper providers and the run service."""
from __future__ import annotations

import pytest

from backend.app.scraper.base import ScraperError
from backend.app.scraper.mock import MockClient


def test_mock_returns_realistic_stats():
    c = MockClient(recent_media_count=12)
    stats = c.get_stats("natgeo")
    assert stats.username == "natgeo"
    assert stats.follower_count > 0
    assert stats.following_count > 0
    assert stats.media_count > 0
    assert 0 <= stats.engagement_rate < 50
    assert stats.recent_posts > 0
    assert stats.top_post is not None
    assert stats.top_post["like_count"] > 0


def test_mock_produces_valid_stats():
    c = MockClient()
    a = c.get_stats("nasa")
    b = c.get_stats("nasa")
    for stats in (a, b):
        assert stats.username == "nasa"
        assert 0 < stats.follower_count < 10_000_000
        assert stats.following_count > 0
        assert stats.media_count > 0
        assert 0 <= stats.engagement_rate < 50


def test_overview_top_gainers(client, auth_headers):
    # Two runs build history so 24h changes are computed.
    client.post("/api/handles/bulk", json={"text": "g1, g2, g3, g4, g5, g6, g7, g8, g9, g10, g11, g12"}, headers=auth_headers)
    client.post("/api/handles/check-all", headers=auth_headers)
    client.post("/api/handles/check-all", headers=auth_headers)
    ov = client.get("/api/overview", headers=auth_headers).json()
    tg = ov["top_gainers"]
    assert isinstance(tg, list)
    assert len(tg) <= 10
    if tg:
        assert "username" in tg[0]
        assert "change" in tg[0]
        assert "followers" in tg[0]
        changes = [g["change"] for g in tg]
        assert changes == sorted(changes, reverse=True)


def test_mock_healthcheck():
    ok, msg = MockClient().healthcheck()
    assert ok is True
    assert "mock" in msg.lower()


def test_service_creates_snapshots_and_run_log(client, auth_headers):
    # Add two handles.
    client.post("/api/handles/bulk", json={"text": "alice, bob"}, headers=auth_headers)
    r = client.post("/api/handles/check-all", headers=auth_headers)
    assert r.status_code == 200
    run = r.json()["run"]
    assert run["handles_total"] == 2
    assert run["ok_count"] == 2
    assert run["failed_count"] == 0

    # Snapshots exist and carry follower counts.
    snaps = client.get("/api/snapshots", headers=auth_headers).json()
    assert len(snaps) == 2
    assert all(s["status"] == "ok" for s in snaps)
    assert all(s["follower_count"] > 0 for s in snaps)

    # Overview reflects them.
    ov = client.get("/api/overview", headers=auth_headers).json()
    assert ov["total_handles"] == 2
    assert ov["followers_total"] > 0


def test_bulk_import_dedupes_and_filters(client, auth_headers):
    r = client.post(
        "/api/handles/bulk",
        json={"text": "a, b, a, @b, bad handle!, c"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    # a, b, c added; "@b" deduped; "bad handle!" split into "bad" + invalid "handle!"
    body = r.json()
    assert body["added"] >= 3
    usernames = [h["username"] for h in client.get("/api/handles", headers=auth_headers).json()]
    assert "a" in usernames and "b" in usernames and "c" in usernames
    assert "nasa" not in usernames  # not added


def test_requires_auth(client):
    assert client.get("/api/handles").status_code == 401
    assert client.get("/api/overview").status_code == 401


def test_login_rejects_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_mock_never_fails():
    c = MockClient()
    for name in ["a", "b", "c", "natgeo", "nasa", "xyz", "test", "user1", "user2", "user3"]:
        stats = c.get_stats(name)
        assert stats.follower_count > 0


def test_delete_failed_handles(client, auth_headers):
    from backend.app.database import SessionLocal
    from backend.app import models

    client.post("/api/handles/bulk", json={"text": "keep1, bad1, keep2"}, headers=auth_headers)

    # Mark 'bad1' as failed directly in the DB.
    db = SessionLocal()
    h = db.query(models.Handle).filter(models.Handle.username == "bad1").first()
    h.last_status = "error"
    db.commit()
    db.close()

    r = client.post("/api/handles/delete-failed", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["deleted"] == 1

    usernames = [x["username"] for x in client.get("/api/handles", headers=auth_headers).json()]
    assert "bad1" not in usernames
    assert "keep1" in usernames and "keep2" in usernames


def test_failed_handles_endpoint(client, auth_headers):
    from backend.app.database import SessionLocal
    from backend.app import models

    client.post("/api/handles/bulk", json={"text": "ok1, bad1, ok2"}, headers=auth_headers)

    # Mark 'bad1' as failed directly in the DB.
    db = SessionLocal()
    h = db.query(models.Handle).filter(models.Handle.username == "bad1").first()
    h.last_status = "error"
    h.last_error = "[not_found] Profile not found"
    db.commit()
    db.close()

    r = client.get("/api/handles/failed", headers=auth_headers)
    assert r.status_code == 200
    failed = r.json()
    assert len(failed) == 1
    assert failed[0]["username"] == "bad1"
    assert failed[0]["last_status"] == "error"
    assert "not_found" in (failed[0]["last_error"] or "")
