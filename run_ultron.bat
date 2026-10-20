@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo ==========================================================
echo Starting ULTRON - Personal Autonomous Voice Assistant
echo User: Luffy - Languages: English and Tamil - Continuous Listening
echo ==========================================================

"%~dp0.venv\Scripts\python.exe" main.py
pause
