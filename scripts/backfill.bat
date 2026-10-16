@echo off
chcp 65001 >nul
REM ASCII-only on purpose - see the header note in setup.bat
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

set "TMP=%ROOT%\.tmp"
set "TEMP=%ROOT%\.tmp"
set "TMPDIR=%ROOT%\.tmp"
if not exist "%TMP%" mkdir "%TMP%"
set "PYTHONIOENCODING=utf-8"
set "PY=%ROOT%\.venv\Scripts\python.exe"

echo ============================================================
echo  [1/2] Backfill history (3 years daily + 1 year hourly)
echo        About 5-10 minutes, ~5900 API calls (free quota 10000/day)
echo ============================================================
"%PY%" -m collector.backfill %*
if errorlevel 1 (
    echo.
    echo Backfill FAILED.
    if not defined YRD_NO_PAUSE pause >nul
    exit /b 1
)

echo.
echo ============================================================
echo  [2/2] Bridging the most recent month (reanalysis has a delay)
echo ============================================================
"%PY%" -m collector.pipeline --mode backfill --past-days 30
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Backfill completed.
) else (
    echo Bridge step FAILED ^(exit code %RC%^).
)
if not defined YRD_NO_PAUSE pause >nul
exit /b %RC%
