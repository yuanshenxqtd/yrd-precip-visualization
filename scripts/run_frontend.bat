@echo off
chcp 65001 >nul
title YRD Precip - Frontend (close this window to stop)
REM ASCII-only on purpose - see the header note in setup.bat
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%\frontend"

set "TMP=%ROOT%\.tmp"
set "TEMP=%ROOT%\.tmp"
set "TMPDIR=%ROOT%\.tmp"
if not exist "%TMP%" mkdir "%TMP%"

REM ============================================================
REM  pnpm selection: always prefer the standalone install at
REM  %APPDATA%\npm\pnpm.cmd. Tools like DSH Desktop inject their own
REM  shim earlier in PATH, and the two use different supply-chain
REM  policies - which shows up as "same lockfile works for one,
REM  fails for the other".
REM ============================================================
set "PNPM=%APPDATA%\npm\pnpm.cmd"
if not exist "%PNPM%" set "PNPM=pnpm"

REM Usage: run_frontend.bat [lan]
set "MODE=%~1"
set "HOSTARG="
if /I "%MODE%"=="lan" set "HOSTARG=--host 0.0.0.0"

if not exist "node_modules" (
    echo ============================================================
    echo   First run: installing frontend dependencies, 1-2 minutes
    echo ============================================================
    call "%PNPM%" install
    if errorlevel 1 (
        echo Dependency install FAILED.
        echo If pnpm is missing, install Node.js then run: npm install -g pnpm
        pause
        exit /b 1
    )
)

echo ============================================================
echo   YRD Precipitation - Frontend
echo ============================================================
echo   pnpm : %PNPM%
echo   URL  : http://127.0.0.1:5173
echo.
echo   * Start the backend first (scripts\run_backend.bat), otherwise
echo     the page will show a "cannot reach backend" banner
echo   * Occupies port 5173 only while this window is open
echo   * No auto-start registration of any kind
if /I "%MODE%"=="lan" echo   * LAN mode: phones on the same WiFi can connect
echo ============================================================
echo.

call "%PNPM%" dev %HOSTARG%

echo.
echo Frontend stopped.
if not defined YRD_NO_PAUSE (
    echo Press any key to close ...
    pause >nul
)
