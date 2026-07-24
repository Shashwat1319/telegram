#!/bin/bash
echo "============================================"
echo "  Telegram Affiliate Automation — Setup"
echo "============================================"
echo ""

# Step 1: Copy config
if [ ! -f config.json ]; then
    cp config.example.json config.json 2>/dev/null
    echo "[1/4] Created config.json from template"
else
    echo "[1/4] config.json exists — skipping"
fi

# Step 2: Copy .env
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null
    echo "[2/4] Created .env from template"
    echo "     !!! IMPORTANT: Edit .env with your real tokens !!!"
else
    echo "[2/4] .env exists — skipping"
fi

# Step 3: Install dependencies
echo "[3/4] Installing Python dependencies..."
pip install -r requirements.txt -q 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[3/4] Dependencies installed"
else
    echo "[3/4] WARNING: pip install had issues"
fi

# Step 4: Run demo
echo "[4/4] Running demo..."
echo ""
python demo.py

echo ""
echo "============================================"
echo "  Setup complete!"
echo "  Next: python poster.py  (post a deal)"
echo "        python orchestrator.py  (run bot)"
echo "============================================"
