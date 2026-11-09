#!/usr/bin/env bash
# Build the frontend and serve the full app (API + admin panel) on :8000.
set -euo pipefail
cd "$(dirname "$0")"

# --- Backend deps ---
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi

# --- Frontend build ---
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi
(cd frontend && npm run build)

# --- Run ---
export INSTABI_DATA_DIR="${INSTABI_DATA_DIR:-backend/data}"
exec .venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
