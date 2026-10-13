@echo off
title Bank Queue Management System
color 0B
echo ==============================================================
echo   BANK QUEUE MANAGEMENT SYSTEM
echo   Serving at: http://127.0.0.1:8000
echo ==============================================================
echo.
echo Opening website in your default browser...
start http://127.0.0.1:8000
cd /d "%~dp0python_backend"
py run_server.py
pause
