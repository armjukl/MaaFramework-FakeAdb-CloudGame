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

REM 注入 ADB 配置到 MaaEnd
for %%I in ("%MAAEND_EXE%") do set "MAAEND_DIR=%%~dpI"
set "MAAEND_CONFIG=%MAAEND_DIR%config\mxu-MaaEnd.json"
set "MAAFFACG_ADB_FULL=%~dp0platform-tools\adb.exe"

if exist "%MAAEND_CONFIG%" (
    echo [INFO] 注入 ADB 配置到 MaaEnd...
    call :inject_adb_config "%MAAEND_CONFIG%" "%MAAFFACG_ADB_FULL%"
) else (
    echo [WARN] 未找到 MaaEnd 配置文件，启动后请手动配置
)

echo [INFO] 启动 MaaEnd...
echo.
echo ADB 路径：%MAAFFACG_ADB_FULL%
echo 设备地址：127.0.0.1:5555
echo.
start "MaaEnd" "%MAAEND_EXE%"
pause
exit /b 0

:inject_adb_config
set "CONFIG_FILE=%~1"
set "ADB_PATH=%~2"
powershell -NoProfile -Command ^
    $config = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; ^
    $adbValue = '127.0.0.1:5555-' + '%ADB_PATH:\=\\%'; ^
    $changed = $false; ^
    for ($i = 0; $i -lt $config.instances.Count; $i++) { ^
        $inst = $config.instances[$i]; ^
        if ($inst.controllerName -eq 'ADB') { ^
            if (-not $inst.savedDevice -or -not $inst.savedDevice.adbDeviceName) { ^
                $config.instances[$i].savedDevice = @{ adbDeviceName = $adbValue }; ^
                $changed = $true; ^
            } ^
        } ^
    } ^
    if ($changed) { ^
        $config | ConvertTo-Json -Depth 10 | Set-Content '%CONFIG_FILE%' -Encoding UTF8; ^
        Write-Host '[OK] ADB 配置已注入'; ^
    } else { ^
        Write-Host '[OK] ADB 配置已存在，跳过'; ^
    }
exit /b 0
