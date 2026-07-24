# Telegram Affiliate Automation System

**A fully automated pipeline that generates promotional content, posts to Telegram, tracks affiliate clicks, runs an interactive bot, and manages referrals — all on autopilot via GitHub Actions CI/CD and Netlify serverless.**

> 📖 Read the full story: [How I Built a Telegram Affiliate Bot That Posts Deals 24/7 — Dev.to](https://dev.to/shashwat1319/how-i-built-a-telegram-affiliate-bot-that-posts-deals-247-full-python-source-1an3)

---

## What It Does

This system converts a JSON product feed into a complete Telegram affiliate marketing operation. No manual work after setup.

1. **Content Generation** — Each product becomes 3 promotional variants: pain-fix, deal-alert, short-urgency
2. **Automated Posting** — GitHub Actions posts deals to your Telegram channel every 4 hours
3. **Interactive Bot** — 7 commands: /deal /topdeal /search /referral /about /contact
4. **Click Tracking** — Netlify Edge Functions redirect through affiliate links with per-product analytics
5. **Referral System** — Tiered rewards with real-time join detection
6. **Daily Reports** — Member count, content stats, top referrers delivered to admin

---

## Architecture

```
GitHub Actions (every 4h)
│
├── feeder.py          Products → 3 content variants
├── poster.py          Posts to Telegram with inline buttons
├── referral.py        Referral stats (one-shot)
├── reporting.py       Admin daily report
└── Netlify Deploy     Click tracker functions

Local Orchestrator (auto-start at login)
│
├── bot.py             Interactive Telegram bot
└── referral.py        Join detection + welcome DMs

Netlify Edge Functions
│
├── go.js              Click tracker → affiliate redirect + analytics
├── stats.js           Click statistics
└── subscribe.js       Email newsletter signup
```

---

## Quick Start

```
# 1. Copy config template
cp config.example.json config.json

# 2. Create .env
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate content
python feeder.py --source product_home.json --output content_home.json

# 5. Post a deal
python poster.py

# 6. Push to GitHub → CI takes over
```

**Full step-by-step setup → [SETUP.md](SETUP.md)**

---

## Modules

| Module | Lines | Role |
|--------|-------|------|
| `orchestrator.py` | 212 | Main loop — bot + referral threads + PID lock |
| `bot.py` | 282 | Telegram bot with 7 commands |
| `poster.py` | 198 | Channel poster with HTML formatting + dedup |
| `feeder.py` | 197 | Product-to-content converter (3 formats) |
| `referral.py` | 156 | Referral links + join detection + tiered rewards |
| `reporting.py` | 89 | Daily reports + milestone goals |
| `group_poster.py` | 181 | Cross-post deals to Telegram groups |
| `utils.py` | 68 | Tracked URLs, markdown escaping, ASIN extraction |
| `data.py` | 39 | JSON file I/O with locking |
| `config_loader.py` | 17 | Config with mtime caching |

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Languages | Python 3.12, JavaScript |
| Frameworks | python-telegram-bot v20, Telethon |
| APIs | Telegram Bot API, Telegram MTProto, Amazon Associates |
| Cloud | Netlify (Edge Functions, Blob Store), GitHub Actions |
| Python | asyncio, aiohttp, pillow, python-dotenv, requests |
| Storage | Netlify Blobs, JSON files |

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with channel link |
| `/deal` | Random unposted deal |
| `/topdeal` | Highest discount deal |
| `/search <keyword>` | Search deals by title/category |
| `/referral` | Generate invite link + stats |
| `/about` | Bot description |
| `/contact` | Channel link |

---

## CI/CD Pipeline

Triggered every 4 hours + on push + manually:

1. `feeder.py` → generate content from products
2. `poster.py` → post 1 deal to channel
3. `referral.py --oneshot` → log referral stats
4. `reporting.py --daily` → admin report
5. Netlify deploy → click tracker update
6. Commit updated state back to repo

---

## Product Format

Add products to `product_home.json`:
```json
{
  "products": [
    {
      "name": "Product Name",
      "price": "₹499",
      "mrp": "₹999",
      "discount_percent": "50%",
      "link": "https://amzn.to/your-link",
      "category": "Home & Kitchen",
      "image": "https://images.amazon.in/...jpg",
      "rating": "4.2"
    }
  ]
}
```

Run `python feeder.py` to regenerate 3 promotional formats per product.

---

*Full setup guide: [SETUP.md](SETUP.md)*
