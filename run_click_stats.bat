@echo off
title Budget Deals - Click Analytics
cd /d "d:\Telegram\telegram"
echo Fetching your daily click reports...
echo ================================================
py check_clicks.py
echo.
pause
