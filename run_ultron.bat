@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo =========================================================================
echo  ULTRON - Autonomous AI Operator (Holographic 3D UI + Voice Engine)
echo  Owner: Luffy - English ^& Tamil - PC ^& Mobile Control
echo =========================================================================

"%~dp0.venv\Scripts\python.exe" apps\windows\src\ultron_desktop\app.py
if errorlevel 1 (
    echo.
    echo ULTRON terminated with an error. Falling back to console mode...
    "%~dp0.venv\Scripts\python.exe" main.py
)
pause
