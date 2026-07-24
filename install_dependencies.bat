@echo off
setlocal
cd /d "%~dp0"

set "PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=120000"

set "BOOTSTRAP_PY="
where py >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP_PY=py -3"
if not defined BOOTSTRAP_PY (
    where python >nul 2>nul
    if not errorlevel 1 set "BOOTSTRAP_PY=python"
)

if not defined BOOTSTRAP_PY (
    echo [ERROR] Python 3.10 or later was not found.
    echo Install Python from https://www.python.org/downloads/windows/
    goto :failed
)

%BOOTSTRAP_PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.10 or later is required.
    goto :failed
)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    %BOOTSTRAP_PY% -m venv .venv
    if errorlevel 1 goto :failed
)

set "PYTHON=%CD%\.venv\Scripts\python.exe"

echo [INFO] Upgrading pip...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo [INFO] Installing MaaFFACG with all optional dependencies...
"%PYTHON%" -m pip install -e ".[netease,test]"
if errorlevel 1 goto :failed

echo [INFO] Verifying Python dependencies...
"%PYTHON%" -c "import maaffacg, PIL, playwright"
if errorlevel 1 goto :failed

echo [INFO] Downloading Playwright Chromium...
"%PYTHON%" -m playwright install chromium
if errorlevel 1 goto :failed

echo.
echo [OK] Installation completed. Run ??MaaFFACG.bat to start.
pause
exit /b 0

:failed
echo.
echo [ERROR] Installation failed. Check the messages above and run this script again.
pause
exit /b 1