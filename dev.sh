#!/usr/bin/env bash
# Dev mode: backend with hot-reload on :8000, Vite dev server on :5173.
# The Vite server proxies /api → http://127.0.0.1:8000.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

export INSTABI_DATA_DIR="${INSTABI_DATA_DIR:-backend/data}"

.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 &
BACK=$!
trap 'kill $BACK 2>/dev/null || true' EXIT

(cd frontend && npm run dev)
