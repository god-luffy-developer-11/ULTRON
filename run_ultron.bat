@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo =====================================================================
echo  ULTRON MASTER CONTROL -- PERSONAL AUTONOMOUS AI OPERATOR
echo  User: Luffy | Iron Man Holographic 3D Orb UI | Voice & Vision
echo  PC Control + Android Phone Companion | Multilingual: EN / TA
echo =====================================================================
echo.

if "%1"=="--cli" goto RUN_CLI
if "%1"=="--console" goto RUN_CLI
if "%1"=="-c" goto RUN_CLI

:RUN_DESKTOP
echo [*] Launching ULTRON Native Holographic 3D Desktop Window...
"%~dp0.venv\Scripts\python.exe" apps\windows\src\ultron_desktop\app.py %*
if errorlevel 1 (
    echo.
    echo [*] Desktop window closed or encountered an issue. Falling back to Console mode...
    echo.
    goto RUN_CLI
)
goto END

:RUN_CLI
echo [*] Launching ULTRON Console Mode...
"%~dp0.venv\Scripts\python.exe" main.py %*

:END
pause
