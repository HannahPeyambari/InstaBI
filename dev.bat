@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  InstaBI - development mode ^(Windows^)
echo ============================================================
echo.

if not exist .venv\Scripts\python.exe (
  echo [error] .venv not found. Run "setup.bat" first.
  exit /b 1
)
if not exist frontend\node_modules (
  echo [error] frontend\node_modules not found. Run "setup.bat" first.
  exit /b 1
)

set "INSTABI_DATA_DIR=%~dp0backend\data"

echo Starting backend  ^(hot reload, http://localhost:8000^)...
start "InstaBI backend" cmd /k ".venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"

echo Starting frontend ^(Vite dev server, http://localhost:5173^)...
start "InstaBI frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both dev servers are running in their own windows.
echo Close those windows to stop them.
