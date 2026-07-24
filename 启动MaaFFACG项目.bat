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
    echo [ERROR] No target program specified.
    echo.
    echo Usage:
    echo   1. Drag a MaaFramework project .exe onto this script
    echo   2. Set MAAFFACG_TARGET_EXE in maaffacg.env
    pause
    exit /b 1
)

if not exist "%TARGET_EXE%" (
    echo [ERROR] Target program not found: %TARGET_EXE%
    pause
    exit /b 1
)

echo [INFO] ADB device status:
adb.exe devices 2>&1
echo.
adb.exe -s 127.0.0.1:5555 get-state 2>nul | find /i "device" >nul
if errorlevel 1 (
    echo [WARN] MaaFFACG virtual device (127.0.0.1:5555) not detected.
    echo   Make sure ??MaaFFACG.bat is running and browser is logged in.
    echo   Run: adb.exe devices  (should show 127.0.0.1:5555 device)
    choice /C YN /M "Continue launching"
    if errorlevel 2 exit /b 1
)

echo [INFO] Using ADB: %~dp0platform-tools\adb.exe
echo [INFO] Launching: %TARGET_EXE%
echo.
echo After launch, configure the following in your program's connection settings:
echo   Device address: 127.0.0.1:5555
echo   ADB path: %~dp0platform-tools\adb.exe
echo.
for %%I in ("%TARGET_EXE%") do set "TARGET_DIR=%%~dpI"
start "MaaFramework Project" /D "%TARGET_DIR%" "%TARGET_EXE%"
pause