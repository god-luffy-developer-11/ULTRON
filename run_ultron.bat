@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo ==========================================================
echo          ULTRON - AUTONOMOUS CROSS-DEVICE AI OPERATOR
echo    Windows PC & Android Phone Control | Gemini Brain | Luffy
echo ==========================================================
echo [1] Start ULTRON Voice Agent (Double-Clap Wake & Persistent Voice)
echo [2] Start ULTRON Holographic 3D Orb UI (Webcam Gestures & HUD)
echo [3] Start FULL SUITE (Voice Agent + Holographic UI + Backend API)
echo ==========================================================
set /p opt="Select an option (1, 2, or 3) [Default: 3]: "
if "%opt%"=="" set opt=3

if "%opt%"=="1" (
    echo Starting ULTRON Voice Agent...
    uv run python main.py
    pause
    exit /b
)

if "%opt%"=="2" (
    call "%~dp0run_ultron_ui.bat"
    exit /b
)

if "%opt%"=="3" (
    echo Starting ULTRON Full Suite...
    start "ULTRON Holographic UI & API" cmd /c "%~dp0run_ultron_ui.bat"
    timeout /t 2 > nul
    uv run python main.py
    pause
    exit /b
)
