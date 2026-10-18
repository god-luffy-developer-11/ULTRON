@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0jarvis_repo\src
set JARVIS_VOICE_DEBUG=0

echo ====================================================
echo Starting Jarvis Voice Assistant Daemon (CLI mode)
echo ====================================================

"%~dp0.venv_jarvis\Scripts\python.exe" -m jarvis.daemon
pause
