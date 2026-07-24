@echo off
title Telegram Affiliate Automation — Setup
echo ============================================
echo   Telegram Affiliate Automation — Setup
echo ============================================
echo.

:: Step 1: Copy config
if not exist config.json (
    copy config.example.json config.json >nul
    echo [1/4] Created config.json from template
) else (
    echo [1/4] config.json already exists — skipping
)

:: Step 2: Copy .env
if not exist .env (
    copy .env.example .env >nul
    echo [2/4] Created .env from template
    echo      !!! IMPORTANT: Edit .env with your real tokens !!!
) else (
    echo [2/4] .env already exists — skipping
)

:: Step 3: Install dependencies
echo [3/4] Installing Python dependencies...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% equ 0 (
    echo [3/4] Dependencies installed
) else (
    echo [3/4] WARNING: pip install had issues — check requirements.txt
)

:: Step 4: Run demo
echo [4/4] Running demo...
echo.
python demo.py

echo.
echo ============================================
echo   Setup complete!
echo   Next: python poster.py  (post a deal)
echo         python orchestrator.py  (run bot)
echo ============================================
pause
