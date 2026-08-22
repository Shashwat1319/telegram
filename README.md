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
9. **SEO Website** — `website_gen.py` generates fresh deal pages with tracked links; Netlify deploy optional
10. **Promo Pack** — `promo_daily.py` generates ready-to-paste promotional posts (W1/W2/W3 playbook)

---

## Architecture

```
GitHub Actions (every 4h)
│
├── feeder.py          Products → 6 content variants
├── website_gen.py     Deal pages → SEO website (tracked links)
├── validate_links.py  QA: no broken affiliate links
├── poster.py          Posts to Telegram with inline buttons
├── referral.py        Referral stats (one-shot)
├── reporting.py       Admin daily report
└── Netlify Deploy     Click tracker + website (optional)

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
| `website_gen.py` | 160 | SEO deal pages with tracked links |
| `validate_links.py` | 90 | Link QA (content + website buyLinks) |
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

Triggered every 4 hours + on push + manually:

1. `feeder.py` → generate content from products
2. `website_gen.py` → regenerate website deal pages (tracked links)
3. `validate_links.py` → QA (0 broken links required)
4. `poster.py` → post 1 deal to channel
5. `referral.py --oneshot` → log referral stats
6. `reporting.py --daily` → admin report
7. Netlify deploy → click tracker + website (if `WEBSITE_NETLIFY_SITE_ID` set)
8. Commit updated state + deal pages back to repo

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
- **`website_gen.py`** — `python website_gen.py --source product_home.json --out website/src/content/deals` regenerates SEO deal pages with tracked `go?url=` links. Deployed automatically by CI if configured.
- **`validate_links.py`** — `python validate_links.py` checks every content item and website page has a valid tracked link; CI fails the build on any broken link.

---

*Full setup guide: [SETUP.md](SETUP.md)*
