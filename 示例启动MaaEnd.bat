@echo off
setlocal
cd /d "%~dp0"

set "PATH=%~dp0platform-tools;%PATH%"
set "ADB_SERVER_SOCKET=tcp:127.0.0.1:5037"
set "MAAEND_EXE="
if exist "maaffacg.env" (
    for /f "tokens=1,* delims==" %%A in (maaffacg.env) do (
        if /I "%%A"=="MAAFFACG_MAAEND_EXE" set "MAAEND_EXE=%%B"
    )
)
if not defined MAAEND_EXE set "MAAEND_EXE=%~dp0..\..\MaaEnd-win-x86_64-v2.19.0\MaaEnd.exe"

if not exist "%MAAEND_EXE%" (
    echo [ERROR] MaaEnd.exe was not found: %MAAEND_EXE%
    pause
    exit /b 1
)

start "MaaEnd" "%MAAEND_EXE%"
