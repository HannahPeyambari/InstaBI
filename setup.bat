@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  InstaBI - one-time setup ^(Windows^)
echo ============================================================
echo.

REM --- Python virtual environment ---
if exist .venv\Scripts\python.exe goto venv_ok
echo [1/3] Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 goto venv_fail
:venv_ok

REM --- Backend dependencies ---
echo [2/3] Installing backend dependencies...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto pip_fail

REM --- Frontend dependencies ---
if exist frontend\node_modules goto npm_ok
echo [3/3] Installing frontend dependencies...
pushd frontend
call npm install
set "RC=!errorlevel!"
popd
if not "!RC!"=="0" goto npm_fail
:npm_ok

echo.
echo ============================================================
echo  Setup complete.
echo  Run "start.bat" for production, or "dev.bat" for development.
echo ============================================================
endlocal
exit /b 0

:venv_fail
echo [error] Could not create the virtual environment.
echo        Make sure Python 3.10+ is installed and on your PATH.
endlocal
exit /b 1

:pip_fail
echo [error] Backend dependency installation failed.
endlocal
exit /b 1

:npm_fail
echo [error] Frontend dependency installation failed.
echo        Make sure Node.js is installed and on your PATH.
endlocal
exit /b 1
