# Telegram Affiliate Automation System

**A fully automated pipeline that generates promotional content, posts to Telegram, tracks affiliate clicks, runs an interactive bot, and manages referrals — all on autopilot via GitHub Actions CI/CD and Netlify serverless.**

> 📖 Read the full story: [How I Built a Telegram Affiliate Bot That Posts Deals 24/7 — Dev.to](https://dev.to/shashwat1319/how-i-built-a-telegram-affiliate-bot-that-posts-deals-247-full-python-source-1an3)

---

## What It Does

This system converts a JSON product feed into a complete Telegram affiliate marketing operation. No manual work after setup.

1. **Content Generation** — Each product becomes 6 promotional variants: pain-fix, deal-alert, short-urgency, trust-check, price-history, personal-review
2. **Automated Posting** — GitHub Actions posts deals to your Telegram channel every 4 hours (unposted items first, oldest-first reposts after)
3. **Interactive Bot** — 8 commands: /deal /topdeal /search /referral /premium /about /contact
4. **Click Tracking** — Netlify Edge Functions redirect through affiliate links with per-product analytics
5. **Referral System** — Tiered rewards with real-time join detection + 30-day recurring premium unlock
6. **Daily Reports** — Member count, content stats, top referrers, milestone goals + progress bar
7. **Daily Polls** — Engagement poll with the day's top deals
8. **Premium Channel** — Auto-posts exclusive deals to a locked premium channel
9. **Promo Pack** — `promo_daily.py` generates ready-to-paste promotional posts (W1/W2/W3 playbook)

---

## Architecture

```
GitHub Actions (every 4h)
│
├── feeder.py          Products → 6 content variants
├── validate_links.py  QA: no broken affiliate links
├── poster.py          Posts to Telegram with inline buttons
├── referral.py        Referral stats (one-shot)
├── reporting.py       Admin daily report
└── Netlify Deploy     Click tracker

Local Orchestrator (auto-start at login)
│
├── bot.py             Interactive Telegram bot
├── referral.py        Join detection + welcome DMs
└── promo_daily.py     Daily promo post generator (manual)

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
| `bot.py` | 282 | Telegram bot with 8 commands |
| `poster.py` | 198 | Channel poster with HTML formatting + dedup |
| `feeder.py` | 197 | Product-to-content converter (6 formats) |
| `referral.py` | 214 | Referral links + join detection + premium unlock |
| `reporting.py` | 89 | Daily reports + milestone goals |
| `promo_daily.py` | 130 | Daily promo post generator (W1/W2/W3) |
| `validate_links.py` | 64 | Link QA (content) |
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
| `/premium` | Premium channel access (5 referrals unlock 30 days) |
| `/about` | Bot description |
| `/contact` | Channel link |

---

## CI/CD Pipeline

Triggered on push to `main` + manual dispatch (validate & deploy only —
all posting/content generation runs locally via `orchestrator.py`):

1. `validate_links.py` → QA (0 broken links required)
2. Netlify deploy → click tracker (`/go`, `/stats`)

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

Run `python feeder.py` to regenerate 6 promotional formats per product.

---

## Extra Tools

- **`promo_daily.py`** — generates one ready-to-paste promo post per day (from the W1/W2/W3 playbook in `promo_pack.md`), saves to `promo_queue.md`. Run it daily (local or scheduled).
- **`validate_links.py`** — `python validate_links.py` checks every content item has a valid link; CI fails the build on any broken link.
- **`group_roi.py`** — `python group_roi.py` shows per-group post/click ROI from tracker stats; `--apply` pauses zero-click groups (≥6 posts) and unpauses clickers.
- **`seo_weekly.py`** — `python seo_weekly.py` drafts a Dev.to/Medium article from the week's top deals (tracked links, `src=seo`) into `seo_drafts/`.

---

*Full setup guide: [SETUP.md](SETUP.md)*
