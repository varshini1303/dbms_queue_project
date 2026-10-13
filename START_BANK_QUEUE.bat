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

if exist "%~dp0dbms_queue_project\python_backend" (
    cd /d "%~dp0dbms_queue_project\python_backend"
) else if exist "%~dp0python_backend" (
    cd /d "%~dp0python_backend"
) else if exist "%~dp0Bank_Queue_Management_System\python_backend" (
    cd /d "%~dp0Bank_Queue_Management_System\python_backend"
)

py run_server.py
pause
