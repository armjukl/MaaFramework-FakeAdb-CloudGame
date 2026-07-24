@echo off
setlocal
cd /d "%~dp0"

if not exist "platform-tools\adb.exe" (
    echo [ERROR] Missing bundled platform-tools\adb.exe.
    pause
    exit /b 1
)

if not exist "maaffacg.env" (
    copy /y "maaffacg.env.example" "maaffacg.env" >nul
    echo [ERROR] Created maaffacg.env. Configure MAAFFACG_PACKAGE and MAAFFACG_GAME_CODE first.
    pause
    exit /b 1
)

set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
set "PATH=%~dp0platform-tools;%PATH%"
"%PYTHON%" -c "import PIL, playwright" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] MaaFFACG dependencies are missing from %PYTHON%.
    echo Run install_dependencies.bat in this folder, then start MaaFFACG again.
    pause
    exit /b 1
)

"%PYTHON%" -m maaffacg.cli --env "%~dp0maaffacg.env"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
