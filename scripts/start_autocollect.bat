@echo off
chcp 65001 >nul
title YRD Precip - Scheduler (close this window to stop)
REM ASCII-only on purpose - see the header note in setup.bat
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

set "TMP=%ROOT%\.tmp"
set "TEMP=%ROOT%\.tmp"
set "TMPDIR=%ROOT%\.tmp"
if not exist "%TMP%" mkdir "%TMP%"
set "PYTHONIOENCODING=utf-8"

REM Usage:
REM   start_autocollect.bat                  -> every 30 minutes
REM   start_autocollect.bat --interval 60    -> every 60 minutes
REM   start_autocollect.bat --once           -> collect once and exit
set "EXTRA=%*"
if "%EXTRA%"=="" set "EXTRA=--interval 30"

echo ============================================================
echo   YRD Precipitation - Scheduled collection (mode B)
echo ============================================================
echo   Args: %EXTRA%
echo.
echo   * Foreground process: closing this window stops it
echo   * Does NOT auto-start after reboot (no registry / task entry)
echo   * Gaps while stopped are back-filled automatically next run
echo.
echo   Press Ctrl+C or just close this window to stop.
echo ============================================================
echo.

"%ROOT%\.venv\Scripts\python.exe" -m collector.scheduler %EXTRA%

echo.
echo Scheduler stopped.
if not defined YRD_NO_PAUSE (
    echo Press any key to close ...
    pause >nul
)
