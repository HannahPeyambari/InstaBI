@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  InstaBI - production start ^(Windows^)
echo ============================================================
echo.

if not exist .venv\Scripts\python.exe (
  echo [error] .venv not found. Run "setup.bat" first.
  exit /b 1
)

REM Build the frontend once if it hasn't been built yet.
if exist frontend\dist\index.html goto build_done
if not exist frontend\node_modules (
  echo [error] frontend\node_modules not found. Run "setup.bat" first.
  exit /b 1
)
echo [1/2] Building frontend...
pushd frontend
call npm run build
set "RC=!errorlevel!"
popd
if not "!RC!"=="0" (
  echo [error] Frontend build failed.
  exit /b 1
)
:build_done

echo [2/2] Starting server...
set "PORT=8000"
if not "%~1"=="" set "PORT=%~1"
set "INSTABI_DATA_DIR=%~dp0backend\data"

echo.
echo  Admin panel  :  http://localhost:%PORT%
echo  API docs     :  http://localhost:%PORT%/docs
echo  Admin password: backend\data\admin_password.txt
echo.

.venv\Scripts\python -m uvicorn backend.app.main:app --host 0.0.0.0 --port !PORT!
