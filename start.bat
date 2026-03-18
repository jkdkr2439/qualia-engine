@echo off
title Pete Lucison
cd /d "%~dp0"
echo [Pete] Starting server...
start "" python I/server.py
timeout /t 3 /nobreak >nul
start http://localhost:8000
echo [Pete] Monitor: http://localhost:8000
pause
