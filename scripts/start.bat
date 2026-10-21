@echo off
chcp 65001 >nul
title YRD Precip - One-Click Start
setlocal enabledelayedexpansion
REM ASCII-only on purpose - see the header note in setup.bat
REM
REM One-click launcher, in this order:
REM   preflight -> frontend deps -> backend -> wait -> frontend -> wait
REM   -> browser -> scheduled collector -> summary
REM
REM Usage:
REM   start.bat                 start everything
REM   start.bat --no-collect    skip the scheduled collector
REM   start.bat --no-browser    do not open the browser
REM   start.bat lan             listen on 0.0.0.0 (phones on the same WiFi)
REM
REM Each service gets its own window. Close that window to stop it, or run
REM scripts\stop_all.bat to stop the two web services at once.

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

set "TMP=%ROOT%\.tmp"
set "TEMP=%ROOT%\.tmp"
set "TMPDIR=%ROOT%\.tmp"
if not exist "%TMP%" mkdir "%TMP%"
set "PYTHONIOENCODING=utf-8"

set "PY=%ROOT%\.venv\Scripts\python.exe"
set "HOST=127.0.0.1"
set "API_PORT=8000"
set "WEB_PORT=5173"
set "API_URL=http://127.0.0.1:%API_PORT%"
set "WEB_URL=http://127.0.0.1:%WEB_PORT%"

set "OPEN_BROWSER=1"
set "WITH_COLLECT=1"

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="--no-browser" set "OPEN_BROWSER=0"
if /I "%~1"=="--no-collect" set "WITH_COLLECT=0"
if /I "%~1"=="lan" set "HOST=0.0.0.0"
shift
goto :parse_args
:args_done

echo ============================================================
echo   YRD Precipitation - One-Click Start
echo ============================================================
if "%HOST%"=="0.0.0.0" (
    echo   Mode: LAN - other devices on the same WiFi can connect
) else (
    echo   Mode: local only
)
echo.

REM ------------------------------------------------------------- preflight
if not exist "%PY%" (
    echo [ERROR] Python venv not found.
    echo         Expected: %PY%
    echo         Run scripts\setup.bat first.
    goto :fail
)
if not exist "%ROOT%\data\weather.db" (
    echo [ERROR] Database not found: data\weather.db
    echo         Run scripts\init_db.bat then scripts\backfill.bat first.
    goto :fail
)

REM ------------------------------------------------------------- frontend deps
if not exist "%ROOT%\frontend\node_modules" (
    echo [SETUP] Installing frontend dependencies, 1-2 minutes ...
    set "PNPM=%APPDATA%\npm\pnpm.cmd"
    if not exist "!PNPM!" set "PNPM=pnpm"
    pushd "%ROOT%\frontend"
    call "!PNPM!" install
    set "INSTALL_RC=!ERRORLEVEL!"
    popd
    if not "!INSTALL_RC!"=="0" (
        echo.
        echo [ERROR] pnpm install failed - see the output above.
        goto :fail
    )
    echo         done.
    echo.
)

REM ------------------------------------------------------------- backend
set "BACKEND_UP="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%API_PORT% " ^| findstr LISTENING') do set "BACKEND_UP=1"

if defined BACKEND_UP (
    echo [SKIP]  Backend is already listening on port %API_PORT%
) else (
    echo [START] Backend API ...
    start "YRD Backend" /D "%ROOT%" cmd /c call "%ROOT%\scripts\run_backend.bat" %HOST% %API_PORT%
    call :wait_http "%API_URL%/api/health" 90 "Backend"
    if errorlevel 1 goto :fail
)
echo.

REM ------------------------------------------------------------- frontend
set "FRONTEND_UP="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%WEB_PORT% " ^| findstr LISTENING') do set "FRONTEND_UP=1"

if defined FRONTEND_UP (
    echo [SKIP]  Frontend is already listening on port %WEB_PORT%
) else (
    echo [START] Frontend dev server ...
    if "%HOST%"=="0.0.0.0" (
        start "YRD Frontend" /D "%ROOT%" cmd /c call "%ROOT%\scripts\run_frontend.bat" lan
    ) else (
        start "YRD Frontend" /D "%ROOT%" cmd /c call "%ROOT%\scripts\run_frontend.bat"
    )
    call :wait_http "%WEB_URL%/" 120 "Frontend"
    if errorlevel 1 goto :fail
)
echo.

REM ------------------------------------------------------------- browser
if "%OPEN_BROWSER%"=="1" (
    echo [OPEN]  %WEB_URL%
    start "" "%WEB_URL%"
) else (
    echo [SKIP]  Browser not opened ^(--no-browser^)
)
echo.

REM ------------------------------------------------------------- collector
if "%WITH_COLLECT%"=="0" (
    echo [SKIP]  Collector not started ^(--no-collect^)
    goto :summary
)

set "SCHED_PID="
if exist "%TMP%\scheduler.pid" set /p SCHED_PID=<"%TMP%\scheduler.pid"
set "SCHED_ALIVE="
if defined SCHED_PID (
    for /f %%a in ('tasklist /FI "PID eq %SCHED_PID%" /NH 2^>nul ^| findstr /C:"%SCHED_PID%"') do set "SCHED_ALIVE=1"
)
if defined SCHED_ALIVE (
    echo [SKIP]  Collector already running ^(PID %SCHED_PID%^)
) else (
    echo [START] Scheduled collector, every 30 minutes ...
    start "YRD Collector" /D "%ROOT%" cmd /c call "%ROOT%\scripts\start_autocollect.bat"
)
echo.

:summary
echo ============================================================
echo   Ready
echo ============================================================
echo   Frontend : %WEB_URL%
echo   API docs : %API_URL%/docs
echo   API base : %API_URL%/api
echo.
echo   Each service runs in its own window.
echo     * close that window to stop that service
echo     * scripts\stop_all.bat stops both web services at once
echo     * scripts\status.bat shows what is listening
echo ============================================================
if not defined YRD_NO_PAUSE pause >nul
exit /b 0

REM ------------------------------------------------------------- helpers
:wait_http
set "WAIT_URL=%~1"
set "WAIT_MAX=%~2"
set "WAIT_LABEL=%~3"
set /a WAIT_N=0
echo         waiting for %WAIT_LABEL% to respond ...
:wait_http_loop
set /a WAIT_N+=1
set "WAIT_CODE="
for /f %%c in ('curl -s -o NUL -m 2 -w "%%{http_code}" "%WAIT_URL%" 2^>nul') do set "WAIT_CODE=%%c"
if "%WAIT_CODE%"=="200" (
    echo         %WAIT_LABEL% ready after about %WAIT_N% seconds
    exit /b 0
)
if %WAIT_N% GEQ %WAIT_MAX% (
    echo         [ERROR] %WAIT_LABEL% did not respond within %WAIT_MAX% seconds
    echo         Open the %WAIT_LABEL% window to see the error message.
    exit /b 1
)
ping -n 2 127.0.0.1 >nul
goto :wait_http_loop

:fail
echo.
echo [FAILED] Startup aborted.
echo          Already-started services are in their own windows.
echo          Run scripts\stop_all.bat to clean up if needed.
if not defined YRD_NO_PAUSE pause >nul
exit /b 1
