@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo =========================================================================
echo  Starting ULTRON Holographic 3D Desktop Operator (Iron Man UI)
echo  User: Luffy - Real PC & Mobile Automation - Continuous Voice & Gestures
echo =========================================================================

"%~dp0.venv\Scripts\python.exe" apps\windows\src\ultron_desktop\app.py
pause
