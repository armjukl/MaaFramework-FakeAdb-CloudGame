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
    echo [ERROR] 未指定目标程序。
    echo.
    echo 使用方法（任选其一）：
    echo   1. 将 MaaFramework 项目的 .exe 拖到这个脚本上
    echo   2. 在 maaffacg.env 中设置 MAAFFACG_TARGET_EXE=路径
    pause
    exit /b 1
)

if not exist "%TARGET_EXE%" (
    echo [ERROR] 找不到目标程序：%TARGET_EXE%
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
    choice /C YN /M "继续启动目标程序"
    if errorlevel 2 exit /b 1
)

echo [INFO] 正在启动：%TARGET_EXE%
for %%I in ("%TARGET_EXE%") do set "TARGET_DIR=%%~dpI"
start "MaaFramework Project" /D "%TARGET_DIR%" "%TARGET_EXE%"
echo [OK] 已启动，请在目标程序中连接设备 127.0.0.1:5555
