@echo off
title Bank Queue Management System - Public Online Access
color 0A
echo =========================================================================
echo   BANK QUEUE MANAGEMENT SYSTEM - PUBLIC ONLINE LAUNCHER
echo =========================================================================
echo.
echo 1. Starting Backend Web Application on port 8000...
start "BankQueue Backend" /B py "%~dp0python_backend\run_server.py"
timeout /t 3 >nul

echo 2. Launching Cloudflare Public Secure Tunnel...
echo.
"%~dp0cloudflared.exe" tunnel --url http://127.0.0.1:8000
pause
