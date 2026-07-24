@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PROXY_URL=socks5h://127.0.0.1:10808"
set "HTTP_PROXY=%PROXY_URL%"
set "HTTPS_PROXY=%PROXY_URL%"
set "ALL_PROXY=%PROXY_URL%"
set "NO_PROXY=localhost,127.0.0.1"
set "PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=120000"
echo [INFO] Using SOCKS5 proxy at 127.0.0.1:10808.

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
"%PYTHON%" -c "import socks" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Installing PySocks bootstrap dependency without the proxy...
    set "HTTP_PROXY="
    set "HTTPS_PROXY="
    set "ALL_PROXY="
    "%PYTHON%" -m pip install PySocks
    if errorlevel 1 (
        echo [ERROR] PySocks bootstrap installation failed.
        goto :failed
    )
    set "HTTP_PROXY=%PROXY_URL%"
    set "HTTPS_PROXY=%PROXY_URL%"
    set "ALL_PROXY=%PROXY_URL%"
)

echo [INFO] Upgrading pip...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo [INFO] Installing MaaFFACG dependencies...
"%PYTHON%" -m pip install -e "."
if errorlevel 1 goto :failed

echo [INFO] Verifying Python dependencies...
"%PYTHON%" -c "import maaffacg, PIL, playwright"
if errorlevel 1 goto :failed

echo [INFO] Downloading Playwright Chromium...
"%PYTHON%" -m playwright install chromium
if errorlevel 1 goto :failed

echo.
echo [OK] Installation completed. Start MaaFFACG with the launcher batch file.
pause
exit /b 0

:failed
echo.
echo [ERROR] Installation failed. Review the messages above and run this script again.
pause
exit /b 1
