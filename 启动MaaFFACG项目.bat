@echo off
setlocal
cd /d "%~dp0"

set "PATH=%~dp0platform-tools;%PATH%"
set "ADB_SERVER_SOCKET=tcp:127.0.0.1:5037"
set "TARGET_EXE=%~1"
if not defined TARGET_EXE if exist "maaffacg.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("maaffacg.env") do (
        if /I "%%A"=="MAAFFACG_TARGET_EXE" set "TARGET_EXE=%%B"
    )
)

if not defined TARGET_EXE (
    echo [ERROR] Drag a MaaFramework program .exe onto this script, or set MAAFFACG_TARGET_EXE in maaffacg.env.
    exit /b 1
)

if not exist "%TARGET_EXE%" (
    echo [ERROR] MaaFramework program was not found: %TARGET_EXE%
    exit /b 1
)

for %%I in ("%TARGET_EXE%") do set "TARGET_DIR=%%~dpI"
start "MaaFramework Project" /D "%TARGET_DIR%" "%TARGET_EXE%"
