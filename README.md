# InstaBI

Track Instagram accounts on a schedule. Give it a list of handles and it
periodically scrapes their stats (followers, following, posts, engagement) and
stores a time series you can browse in a web admin panel.

- **Backend:** Python · FastAPI · SQLAlchemy (SQLite) · APScheduler
- **Scraper:** [instagrapi](https://github.com/instaloader/instagrapi) (unofficial Instagram API) with a built-in **mock** provider for demos
- **Frontend:** React · Vite · Recharts
- **Auth:** simple login, HMAC-signed tokens

## Quick start (demo mode — no Instagram credentials)

```bash
# from repo root
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

(cd frontend && npm install && npm run build)

.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. On first boot a random admin password is written to
`backend/data/admin_password.txt` — use it to sign in (username `admin`).

The default provider is `mock`, so it produces realistic demo data for any
handle — add handles on the **Handles** page and click **Check all**.

## Using real Instagram accounts

The `instagrapi` provider logs in to Instagram with your credentials and scrapes
real stats. Configure it either via environment/`.env`:

```bash
cp backend/.env.example backend/.env
# edit backend/.env:
#   INSTABI_SCRAPER_PROVIDER=instagrapi
#   INSTABI_INSTA_USERNAME=your_username
#   INSTABI_INSTA_PASSWORD=your_password
```

…or through the **Settings** page in the admin panel (provider, credentials,
proxy). The login session is cached to `backend/data/instagrapi_session.pkl` so
repeated runs don't re-authenticate.

> **Heads up:** scraping Instagram violates its Terms of Service and Instagram
> actively blocks automated access (rate limits, login challenges, IP blocks).
> Use a dedicated/throwaway account, add pacing (`per_handle_delay`), and expect
> occasional failures. For compliance-sensitive use, prefer Instagram's official
> Graph API. This project is for research/personal tracking only.

## How it works

```
handles ──▶ scheduler (daily cron) ──▶ scraper service ──▶ instagrapi / mock
   │                                      │                    │
   │                                      ▼                    ▼
   └──────────────── snapshots (SQLite) ◀────────────────────┘
                                   │
                                   ▼
                              admin panel (React)
```

- You add handles (single or bulk paste).
- The scheduler fires a cron expression (default `0 3 * * *` = daily 03:00 UTC).
- Each handle is scraped for its profile stats plus engagement from the most
  recent N posts (likes, comments, views, top post, engagement rate).
- Every result is stored as a **snapshot** with a timestamp → trends/charts.
- Per-handle errors are captured and shown in the panel, not fatal.

## API

REST API under `/api` (see `/docs` for the interactive schema). Key endpoints:

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/auth/login` | Sign in, returns a bearer token |
| GET/POST | `/api/handles` | List / add a handle |
| POST | `/api/handles/bulk` | Bulk import from pasted text |
| PUT/DELETE | `/api/handles/{id}` | Update (pause/resume) / remove |
| POST | `/api/handles/{id}/check` | Scrape one handle now |
| POST | `/api/handles/check-all` | Scrape all active handles |
| GET | `/api/overview` | Aggregate stats + trend series |
| GET | `/api/compare` | Latest stats for every handle |
| GET | `/api/handles/{id}/snapshots` | Time series for one handle |
| GET | `/api/runs` | Run history |
| GET/PUT | `/api/settings` | View/edit scraper + scheduler settings |
| GET | `/api/scheduler` | Scheduler status + next run |
| POST | `/api/scheduler/run` | Run a check now |

## Development

```bash
# terminal 1 — backend (with hot reload)
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# terminal 2 — frontend dev server (proxies /api → :8000)
cd frontend && npm run dev
```

Run tests:

```bash
.venv/bin/python -m pytest backend/tests -q
```

## Configuration

All settings are env vars (prefix `INSTABI_`) or entries in `backend/.env` — see
`backend/.env.example`. The most important:

| Var | Default | Meaning |
| --- | ------- | ------- |
| `INSTABI_SCRAPER_PROVIDER` | `mock` | `mock` or `instagrapi` |
| `INSTABI_INSTA_USERNAME` / `_PASSWORD` | — | Instagram login (instagrapi only) |
| `INSTABI_SCHEDULE_CRON` | `0 3 * * *` | 5-field cron (UTC) |
| `INSTABI_SCHEDULE_ENABLED` | `true` | Toggle the periodic scheduler |
| `INSTABI_PER_HANDLE_DELAY` | `2.0` | Seconds between handles (pacing) |
| `INSTABI_RECENT_MEDIA_COUNT` | `12` | Recent posts sampled for engagement |
| `INSTABI_ADMIN_PASSWORD` | generated | Panel login password |

## Project layout

```
backend/
  app/
    config.py            env + settings
    database.py          SQLAlchemy (SQLite, WAL)
    models.py            Handle, Snapshot, RunLog, Setting
    auth.py              HMAC token auth
    runtime_config.py    runtime-editable settings (panel)
    scheduler.py         APScheduler cron job
    scraper/
      base.py            ScraperClient interface + ProfileStats
      mock.py            demo provider
      instagrapi_client.py  real provider (login, session, engagement)
      manager.py         provider factory + caching
      service.py         run orchestration + snapshot persistence
    api/                 FastAPI routers
    main.py              app entrypoint (serves built frontend + API)
  tests/
  .env.example
frontend/
  src/
    pages/               Dashboard, Handles, Analytics, Runs, Settings, Login
    components/          Layout, shared UI
    api.js, auth.jsx
```

## License

MIT — for personal/research use. You are responsible for how you use it and for
complying with Instagram's Terms of Service.
