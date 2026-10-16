@echo off
chcp 65001 >nul
title YRD Precip - Stop Services
setlocal enabledelayedexpansion
REM ASCII-only on purpose - see the header note in setup.bat

echo ============================================================
echo   YRD Precipitation - Stop Services
echo ============================================================
echo.
echo   Will run "taskkill /T /F" on whatever listens on
echo   port 8000 (backend) and port 5173 (frontend).
echo.

set "STOPPED=0"

for %%P in (8000 5173) do call :killport %%P

echo.
REM redirect-safe delay (timeout fails when stdin is redirected)
ping -n 2 127.0.0.1 >nul
echo   After stop:
for %%P in (8000 5173) do call :verifyport %%P

echo.
if "!STOPPED!"=="0" (
    echo   Nothing was listening - no action needed.
) else (
    echo   Done. Port owners killed: !STOPPED! ^(children included^).
)
echo.
echo   Note: this script locates processes by the port they listen on,
echo         so it works no matter who started them.
echo.
endlocal
if not defined YRD_NO_PAUSE pause >nul
exit /b 0

:killport
set "PORT=%~1"
set "HIT="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% " ^| findstr LISTENING') do (
    set "HIT=1"
    echo   Port %PORT%  -^>  killing PID %%a and its children
    taskkill /PID %%a /T /F >nul 2>nul
    set /a STOPPED+=1
)
if not defined HIT echo   Port %PORT%  -^>  not listening, skipped
exit /b 0

:verifyport
set "PORT=%~1"
set "ALIVE="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% " ^| findstr LISTENING') do set "ALIVE=1"
if defined ALIVE (echo     Port %PORT%: STILL LISTENING - please check manually) else (echo     Port %PORT%: released)
exit /b 0
