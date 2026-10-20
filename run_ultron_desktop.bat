@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo =====================================================================
echo  ULTRON HOLOGRAPHIC 3D DESKTOP OPERATOR (IRON MAN UI)
echo  User: Luffy - Real PC Control, Phone Companion, Voice & Diagnostics
echo =====================================================================

"%~dp0.venv\Scripts\python.exe" apps\windows\src\ultron_desktop\app.py
if errorlevel 1 (
    echo.
    echo ULTRON Desktop terminated with an error.
    pause
)
