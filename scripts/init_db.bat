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

"%ROOT%\.venv\Scripts\python.exe" -m collector.init_db
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Database initialized successfully.
) else (
    echo Initialization FAILED ^(exit code %RC%^).
)
if not defined YRD_NO_PAUSE pause >nul
exit /b %RC%
