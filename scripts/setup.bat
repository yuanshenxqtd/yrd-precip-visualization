@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  NOTE: keep every .bat in this folder ASCII-only.
REM  cmd.exe parses .bat files byte-wise using the active code page
REM  (936/GBK on this machine). Non-ASCII characters inside a UTF-8
REM  .bat get split mid-byte and corrupt the whole script.
REM  All Chinese output comes from Python, which handles UTF-8 fine.
REM ============================================================

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

REM Temp dir must live inside the workspace (see README, environment notes)
set "TMP=%ROOT%\.tmp"
set "TEMP=%ROOT%\.tmp"
set "TMPDIR=%ROOT%\.tmp"
if not exist "%TMP%" mkdir "%TMP%"

set "PY=%ROOT%\.venv\Scripts\python.exe"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"
set "PIPFLAGS=--disable-pip-version-check --no-cache-dir --progress-bar off -i %MIRROR%"

echo ============================================================
echo   YRD Precipitation - Environment Setup
echo   Root : %ROOT%
echo   Temp : %TMP%
echo ============================================================
echo.

echo [1/3] Checking virtual environment ...
if not exist "%PY%" (
    echo       Creating .venv ...
    python -m venv .venv
    if errorlevel 1 goto :err
) else (
    echo       .venv already exists
)

echo [2/3] Upgrading pip ...
"%PY%" -m pip install %PIPFLAGS% --upgrade pip
if errorlevel 1 goto :err

echo [3/3] Installing dependencies ...
"%PY%" -m pip install %PIPFLAGS% -r requirements.txt
if errorlevel 1 goto :err

echo.
echo ============================================================
echo   Done. Verifying imports ...
echo ============================================================
"%PY%" -c "import fastapi, uvicorn, sqlalchemy, apscheduler; print('  fastapi     ', fastapi.__version__); print('  uvicorn     ', uvicorn.__version__); print('  sqlalchemy  ', sqlalchemy.__version__); print('  apscheduler ', apscheduler.__version__)"
echo.
echo All set.
if not defined YRD_NO_PAUSE pause >nul
exit /b 0

:err
echo.
echo [FAILED] previous step returned error %ERRORLEVEL%
if not defined YRD_NO_PAUSE pause >nul
exit /b 1
