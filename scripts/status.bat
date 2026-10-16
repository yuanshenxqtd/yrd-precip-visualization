@echo off
chcp 65001 >nul
title YRD Precip - Service Status
setlocal enabledelayedexpansion
REM ASCII-only on purpose - see the header note in setup.bat

echo ============================================================
echo   YRD Precipitation - Service Status
echo ============================================================
echo.

for %%P in (8000 5173) do call :checkport %%P

echo.
echo   Port 8000 = Backend API (FastAPI)
echo   Port 5173 = Frontend dev server (Vite)
echo   "not listening" means that service is currently stopped.
echo.

endlocal
if not defined YRD_NO_PAUSE pause >nul
exit /b 0

:checkport
set "PORT=%~1"
set "FOUND="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% " ^| findstr LISTENING') do (
  set "FOUND=1"
  set "PNAME=?"
  for /f "tokens=1" %%n in ('tasklist /FI "PID eq %%a" /FO TABLE /NH 2^>nul') do set "PNAME=%%n"
  echo   Port %PORT%   LISTENING   PID %%a   !PNAME!
)
if not defined FOUND echo   Port %PORT%   not listening
exit /b 0
