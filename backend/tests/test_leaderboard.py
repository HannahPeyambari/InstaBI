from datetime import datetime, timedelta


def test_leaderboard_growth_and_periods(client, auth_headers):
    from backend.app.database import SessionLocal
    from backend.app.models import Handle, Snapshot

    now = datetime(2026, 11, 9, 12)
    with SessionLocal() as db:
        for name, baseline, current, active in [
            ("large", 10000, 11000, True),
            ("small", 100, 150, True),
            ("loss", 100, 90, True),
            ("zero", 0, 10, True),
            ("inactive", 10, 99999, False),
        ]:
            handle = Handle(username=name, active=active)
            db.add(handle)
            db.flush()
            for days, count, status in [(7, baseline, "ok"), (6, 999999, "error"), (0, current, "ok")]:
                db.add(Snapshot(handle_id=handle.id, username=name,
                                captured_at=now - timedelta(days=days),
                                follower_count=count, status=status))
        fresh = Handle(username="fresh")
        db.add(fresh)
        db.flush()
        db.add(Snapshot(handle_id=fresh.id, username="fresh", captured_at=now,
                        follower_count=500, status="ok"))
        db.commit()

    response = client.get("/api/leaderboard?period=7", headers=auth_headers)
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert [e["username"] for e in entries] == ["large", "small", "zero", "loss"]
    assert entries[0]["gained"] == 1000
    assert entries[0]["pct"] == 10
    assert entries[2]["pct"] is None
    assert entries[3]["gained"] == -10
    pct = client.get("/api/leaderboard?period=7&sort=pct", headers=auth_headers).json()["entries"]
    assert [e["username"] for e in pct] == ["small", "large", "loss", "zero"]
    assert client.get("/api/leaderboard?period=30", headers=auth_headers).json()["entries"] == []


def test_leaderboard_validation_and_auth(client, auth_headers):
    assert client.get("/api/leaderboard").status_code == 401
    for query in ["period=0", "period=366", "sort=invalid"]:
        assert client.get(f"/api/leaderboard?{query}", headers=auth_headers).status_code == 422
    assert client.get("/api/leaderboard", headers=auth_headers).json()["entries"] == []
