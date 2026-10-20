@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul

echo ==========================================================
echo Starting ULTRON Holographic Orb UI & API Gateway
echo User: Luffy - Iron Man Holographic 3D Orb & Hand Gestures
echo ==========================================================

echo [1/3] Starting ULTRON API Backend on http://127.0.0.1:8000 ...
start "ULTRON API Gateway" /min cmd /c "uv run uvicorn services.api.main:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting ULTRON Holographic UI on http://localhost:3000 ...
cd ui
start "ULTRON Holographic UI" /min cmd /c "npm.cmd run dev"

timeout /t 3 > nul
echo [3/3] Opening Holographic Orb Interface ...
start http://localhost:3000

echo ULTRON Holographic UI and API Gateway are running!
echo Press any key to close this launcher.
pause
