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

echo [INFO] ADB 设备状态：
adb.exe devices 2>&1
echo.
adb.exe -s 127.0.0.1:5555 get-state 2>nul | find /i "device" >nul
if errorlevel 1 (
    echo [WARN] 未检测到 MaaFFACG 虚拟设备（127.0.0.1:5555）
    echo   请确认已先运行 启动MaaFFACG.bat 且浏览器已登录
    echo   然后运行：adb.exe devices
    echo   应看到 127.0.0.1:5555 device
    choice /C YN /M "继续启动"
    if errorlevel 2 exit /b 1
)

echo [INFO] 使用 ADB：%~dp0platform-tools\adb.exe
echo [INFO] 启动目标程序：%TARGET_EXE%
echo.
echo 目标程序启动后，请在连接设置中手动配置：
echo   设备地址：127.0.0.1:5555
echo   ADB 路径：%~dp0platform-tools\adb.exe
echo.
for %%I in ("%TARGET_EXE%") do set "TARGET_DIR=%%~dpI"
start "MaaFramework Project" /D "%TARGET_DIR%" "%TARGET_EXE%"
pause
