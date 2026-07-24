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

echo [INFO] 检查 MaaFFACG 虚拟设备...
adb.exe get-state 2>nul | find /i "device" >nul 2>nul
if errorlevel 1 (
    echo [WARN] MaaFFACG 虚拟设备未就绪，请确认：
    echo   1. 已先运行 启动MaaFFACG.bat（保持窗口不关）
    echo   2. adb.exe devices -l 应看到 127.0.0.1:5555 device
    echo.
    choice /C YN /M "继续启动 MaaEnd"
    if errorlevel 2 exit /b 1
)

echo [INFO] 正在启动 MaaEnd...
start "MaaEnd" "%MAAEND_EXE%"
echo [OK] 已启动 MaaEnd，请在连接设置中使用：
echo   设备地址：127.0.0.1:5555
echo   ADB 路径：%~dp0platform-tools\adb.exe
