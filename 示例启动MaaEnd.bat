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

echo [INFO] ADB 设备状态：
adb.exe devices 2>&1
echo.
adb.exe -s 127.0.0.1:5555 get-state 2>nul | find /i "device" >nul
if errorlevel 1 (
    echo [WARN] 未检测到 MaaFFACG 虚拟设备（127.0.0.1:5555）
    echo   请确认已先运行 启动MaaFFACG.bat 且浏览器已登录
    echo.
    choice /C YN /M "继续启动 MaaEnd"
    if errorlevel 2 exit /b 1
)

echo [INFO] 启动 MaaEnd...
echo.
echo MaaEnd 启动后，请在连接设置中配置：
echo   设备地址：127.0.0.1:5555
echo   ADB 路径：%~dp0platform-tools\adb.exe
echo.
start "MaaEnd" "%MAAEND_EXE%"
pause
