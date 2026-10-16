@echo off
chcp 65001 >nul
title YRD Precip - Backend API (close this window to stop)
REM ASCII-only on purpose - see the header note in setup.bat
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

set "TMP=%ROOT%\.tmp"
set "TEMP=%ROOT%\.tmp"
set "TMPDIR=%ROOT%\.tmp"
if not exist "%TMP%" mkdir "%TMP%"
set "PYTHONIOENCODING=utf-8"

REM Usage: run_backend.bat [host] [port]
REM   local (default) : run_backend.bat
REM   LAN access      : run_backend.bat 0.0.0.0 8000
set "HOST=%~1"
if "%HOST%"=="" set "HOST=127.0.0.1"
set "PORT=%~2"
if "%PORT%"=="" set "PORT=8000"

echo ============================================================
echo   YRD Precipitation - Backend API
echo ============================================================
echo   Listen : http://%HOST%:%PORT%
echo   Docs   : http://127.0.0.1:%PORT%/docs
echo.
echo   * Occupies the port only while this window is open
echo   * No auto-start registration of any kind
if "%HOST%"=="0.0.0.0" echo   * LAN mode: phones on the same WiFi can connect
echo ============================================================
echo.

"%ROOT%\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host %HOST% --port %PORT% --reload

echo.
echo Backend stopped.
if not defined YRD_NO_PAUSE (
    echo Press any key to close ...
    pause >nul
)
