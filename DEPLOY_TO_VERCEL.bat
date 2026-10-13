@echo off
title Deploy Bank Queue Management System to Vercel
color 0B
echo =========================================================================
echo   DEPLOY BANK QUEUE MANAGEMENT SYSTEM TO VERCEL
echo =========================================================================
echo.
echo This script will publish your project to Vercel (https://vercel.com).
echo.
echo - If this is your first time, Vercel will open a browser window to log in.
echo - Simply press Enter to accept the default options when prompted.
echo.
pause
echo.
echo Deploying to Vercel...
cd /d "%~dp0dbms_queue_project"
npx vercel
echo.
echo =========================================================================
echo   If you want to deploy straight to Production, run: npx vercel --prod
echo =========================================================================
pause
