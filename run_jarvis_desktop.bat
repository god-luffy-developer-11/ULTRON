@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0jarvis_repo\src
set JARVIS_VOICE_DEBUG=0

echo ====================================================
echo Starting Jarvis Desktop App (Floating Face ^& Tray)
echo ====================================================

"%~dp0.venv_jarvis\Scripts\python.exe" -m desktop_app
pause
