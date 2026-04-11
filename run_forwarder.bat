@echo off
:: This script runs the Telegram Auto Forwarder in a PERSISTENT loop.
:: It will check for new deals every 1 hour automatically.
cd /d "%~dp0"
echo [%date% %time%] Starting Hourly Auto Forwarder Loop... >> forwarder_log.txt
py auto_forwarder.py >> forwarder_log.txt 2>&1
echo [%date% %time%] Loop Terminated. >> forwarder_log.txt
