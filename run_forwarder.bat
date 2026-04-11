@echo off
:: This script runs the Telegram Auto Forwarder once.
:: Tailored for Windows Task Scheduler.
cd /d "%~dp0"
echo [%date% %time%] Syncing... >> forwarder_log.txt
py auto_forwarder.py >> forwarder_log.txt 2>&1
echo [%date% %time%] Done. >> forwarder_log.txt
