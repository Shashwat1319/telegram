@echo off
title Budget Deals - Auto Forwarder
cd /d "d:\Telegram\telegram"
echo Starting Auto Forwarder...
echo If OTP is asked, type it here and press Enter.
echo ================================================
py auto_forwarder.py
echo.
echo Done! Window will stay open for 30 seconds...
timeout /t 30
