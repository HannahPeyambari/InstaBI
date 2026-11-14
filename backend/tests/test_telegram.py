from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


def test_token_masked(client, auth_headers):
    from backend.app import runtime_config as cfg
    old = dict(cfg._overrides)
    try:
        response = client.put('/api/settings', headers=auth_headers,
                              json={'telegram_bot_token': 'test-private-token'})
        assert response.status_code == 200
        assert 'test-private-token' not in response.text
        assert response.json()['changes']['telegram_bot_token'] == '********'
        assert 'test-private-token' not in client.get('/api/settings', headers=auth_headers).text
        client.put('/api/settings', headers=auth_headers, json={'telegram_bot_token': '********'})
        assert cfg.get('telegram_bot_token') == 'test-private-token'
    finally:
        cfg._overrides = old


def test_render_and_send(client, auth_headers):
    from backend.app import runtime_config as cfg
    from backend.app.database import SessionLocal
    from backend.app.models import Handle, Snapshot
    from backend.app.telegram_report import render_report, send_report
    with SessionLocal() as db:
        with pytest.raises(ValueError, match='two days'):
            render_report(db)
        handle = Handle(username='example')
        db.add(handle)
        db.flush()
        for day, count in [(2, 100), (0, 120)]:
            db.add(Snapshot(handle_id=handle.id, username='example', status='ok',
                            follower_count=count, captured_at=datetime(2026, 11, 9) - timedelta(days=day)))
        db.commit()
        image, caption = render_report(db)
        assert image.startswith(b'\x89PNG')
        assert len(caption) <= 1024
    old = dict(cfg._overrides)
    cfg._overrides.update(telegram_bot_token='private', telegram_chat_id='-1003859629054', telegram_thread_id=405)
    try:
        with patch('backend.app.telegram_report.httpx.post') as post:
            post.return_value.status_code = 200
            post.return_value.json.return_value = {'ok': True}
            send_report()
            assert post.call_args.kwargs['data']['message_thread_id'] == '405'
            assert post.call_args.kwargs['data']['chat_id'] == '-1003859629054'
            post.return_value.status_code = 403
            with pytest.raises(ValueError, match='delivery failed') as error:
                send_report()
            assert 'private' not in str(error.value)
    finally:
        cfg._overrides = old
    assert client.post('/api/settings/telegram/test').status_code == 401


def test_telegram_validation(client, auth_headers):
    for body in [{'telegram_period': 0}, {'telegram_thread_id': -1}, {'telegram_chat_id': 'not-id'}]:
        assert client.put('/api/settings', headers=auth_headers, json=body).status_code == 422


def test_telegram_schedule_independent_of_scraping():
    from backend.app import runtime_config as cfg
    from backend.app import scheduler as scheduling
    old = dict(cfg._overrides)
    try:
        cfg._overrides.update(schedule_enabled=False, telegram_enabled=True)
        with patch.object(scheduling, 'scheduler') as scheduler:
            scheduler.running = False
            scheduling.start_scheduler()
            assert scheduler.add_job.call_args.kwargs['id'] == 'telegram_report'
            assert scheduler.add_job.call_args.kwargs['hours'] == 24
            scheduler.start.assert_called_once()
    finally:
        cfg._overrides = old
