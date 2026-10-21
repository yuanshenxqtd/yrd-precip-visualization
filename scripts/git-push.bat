@echo off
chcp 65001 >nul
title YRD Precip - Commit and Push
REM ASCII-only on purpose - see the header note in setup.bat
setlocal enabledelayedexpansion

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

echo ============================================================
echo   YRD Precipitation - Commit and push to GitHub
echo ============================================================
echo.

if not exist ".git" (
    echo [ERROR] .git not found - run this script from the project folder.
    if not defined YRD_NO_PAUSE pause >nul
    exit /b 1
)

echo -- Remote --
git config --get remote.origin.url
echo.
echo -- Branch --
git rev-parse --abbrev-ref HEAD
echo.

set "DIRTY=0"
for /f "usebackq delims=" %%L in (`git status --porcelain`) do set "DIRTY=1"

if "%DIRTY%"=="0" goto :no_changes

echo -- Changed files --
git status --short
echo.

REM Optional: pass the message as the first argument to skip the prompt
set "MSG=%~1"
if not "%MSG%"=="" goto :have_msg

echo Type a commit message ^(empty = cancel^):
set /p MSG=
if "%MSG%"=="" goto :cancelled

:have_msg
echo.
echo -- Staging and committing --
git add -A
git commit -m "%MSG%"
if errorlevel 1 goto :commit_failed
goto :do_push

:no_changes
echo No local changes.
echo.

:do_push
echo -- Pushing to GitHub --
git push
if errorlevel 1 goto :push_failed

echo.
echo Done.
if not defined YRD_NO_PAUSE pause >nul
exit /b 0

:cancelled
echo.
echo Cancelled - nothing committed.
if not defined YRD_NO_PAUSE pause >nul
exit /b 0

:commit_failed
echo.
echo [FAILED] commit failed.
if not defined YRD_NO_PAUSE pause >nul
exit /b 1

:push_failed
echo.
echo [FAILED] push failed. Things to check:
echo   1. Is Clash Verge running? The GitHub proxy needs it.
echo   2. Run this script again - the network is flaky, a retry often works.
echo   3. If rejected as non-fast-forward, run: git pull --rebase
if not defined YRD_NO_PAUSE pause >nul
exit /b 1
