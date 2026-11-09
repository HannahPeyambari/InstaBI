"""FastAPI application: API + admin panel (built React frontend) + scheduler."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import settings, PROJECT_ROOT
from .database import init_db
from .scheduler import start_scheduler
from .api import auth_routes, handles, runs, settings_api, stats, scheduler_api

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("instabi")

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Materialize a generated admin password on first boot so the user can read
    # it from backend/data/admin_password.txt without triggering a login.
    settings.resolved_admin_password()
    settings.resolved_token_secret()
    start_scheduler()
    log.info("%s started (provider=%s)", settings.app_name, settings.scraper_provider)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(auth_routes.router)
app.include_router(handles.router)
app.include_router(stats.router)
app.include_router(runs.router)
app.include_router(settings_api.router)
app.include_router(scheduler_api.router)


@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.app_name, "provider": settings.scraper_provider}


# --- Serve built frontend (production) ---
if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        # Don't shadow API routes.
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def fallback():
        return HTMLResponse(
            "<h1>InstaBI API</h1>"
            "<p>The admin panel frontend isn't built yet. Run "
            "<code>cd frontend && npm install && npm run build</code>, or use "
            "<code>npm run dev</code> for the dev server.</p>"
            "<p>API docs at <a href='/docs'>/docs</a>. Health: "
            "<a href='/api/health'>/api/health</a></p>"
        )
