@echo off
title Bank Queue Management System - Public Online Access
color 0A
echo =========================================================================
echo   BANK QUEUE MANAGEMENT SYSTEM - PUBLIC ONLINE LAUNCHER
echo =========================================================================
echo.

set "PROJ_DIR=%~dp0"

netstat -ano | findstr :8000 >nul
if %errorlevel% equ 0 (
    echo [OK] Backend server is already running and active on port 8000.
) else (
    echo 1. Starting Backend Web Application on port 8000...
    start "BankQueue Backend" /B py "%PROJ_DIR%\python_backend\run_server.py"
    timeout /t 3 >nul
)

echo 2. Launching Cloudflare Public Secure Tunnel...
echo.
echo =========================================================================
echo Copy the trycloudflare.com link below and share it with anyone!
echo Keep this window OPEN while people are using the website.
echo =========================================================================
echo.
"%PROJ_DIR%\cloudflared.exe" tunnel --url http://127.0.0.1:8000
pause
