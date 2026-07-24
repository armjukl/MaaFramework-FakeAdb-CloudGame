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

echo [INFO] 正在启动：%TARGET_EXE%
for %%I in ("%TARGET_EXE%") do set "TARGET_DIR=%%~dpI"
start "MaaFramework Project" /D "%TARGET_DIR%" "%TARGET_EXE%"
