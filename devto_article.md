---
title: How I Built a Telegram Affiliate Bot That Posts Deals 24/7 — Full Python Source
published: true
description: A fully automated Telegram affiliate marketing system built with Python, GitHub Actions, and Netlify. Generates content, posts deals, tracks clicks, and manages referrals — zero manual work.
tags: python, telegram, automation, githubactions
# cover_image: (optional) add a 1280x720 PNG URL here
---

I wanted a Telegram channel that posts Amazon deals automatically. No manual work. Just set it and forget it.

So I built one.

## What It Does

The system takes a JSON file with products and does everything:

- Converts each product into **3 promotional formats** (pain-fix, deal-alert, short-urgency)
- Posts to Telegram **every 4 hours** via GitHub Actions CI/CD
- Runs an **interactive bot** with 7 commands
- **Tracks every affiliate click** per product via Netlify serverless
- **Detects new members** and sends welcome DMs with referral rewards
- Sends **daily admin reports** with member count and referral stats

All on autopilot. No VPS needed.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Bot Framework | python-telegram-bot v20 |
| MTProto Client | Telethon |
| CI/CD | GitHub Actions (every 4h) |
| Click Tracking | Netlify Edge Functions |
| Storage | JSON files + Netlify Blobs |

## Architecture

```
GitHub Actions (schedule: every 4h)
  ├── feeder.py     → Products → 3 content formats
  ├── poster.py     → Post to Telegram channel
  ├── referral.py   → Referral stats
  ├── reporting.py  → Daily admin report
  └── Netlify Deploy → Click tracker

Local Orchestrator (auto-start)
  ├── bot.py        → Interactive bot (7 commands)
  └── referral.py   → Join detection + welcome DMs
```

## Why I Built It

I was running a Telegram deal channel manually. Finding products, writing posts, formatting links, tracking clicks. It took 1-2 hours daily and I kept missing posting schedules.

I wanted a system that:
- Posts consistently (humans forget, machines don't)
- Tracks every click to know what works
- Grows itself via referrals
- Costs nothing to run

## How It Works

### 1. Product Feed (`product_home.json`)

```json
{
  "products": [
    {
      "name": "Wipro 10W Smart RGBW LED Bulb",
      "price": "₹599",
      "mrp": "₹1799",
      "discount_percent": "67%",
      "link": "https://amzn.to/your-link",
      "category": "Home & Kitchen",
      "rating": "4.2"
    }
  ]
}
```

### 2. Content Generation (`feeder.py`)

Each product becomes 3 posts optimized for different reader psychology:
- **Pain-Fix**: "Tired of dark rooms? Here's the fix."
- **Deal-Alert**: "67% OFF — Wipro Smart LED Bulb"
- **Short-Urgency**: "Limited stock. Grab it now."

### 3. Automated Posting (`poster.py`)

Posts to Telegram with inline buttons — "Buy on Amazon", "Share Deal", "Join Channel". Dedup logic prevents reposting the same product.

### 4. Click Tracking (Netlify)

Every click goes through `go.js` — a Netlify Edge Function that:
- Records the product ID, timestamp, and referrer
- Redirects to Amazon with your affiliate tag
- Returns stats via `stats.js`

### 5. Referral System (`referral.py`)

When someone joins via a referral link:
- They get a welcome DM with bot commands
- The referrer earns points (tiered: 1x, 1.5x, 2x)
- /referral shows progress bars toward next tier

## The Bot Commands

| Command | What it does |
|---------|-------------|
| `/start` | Welcome + channel link |
| `/deal` | Random unposted deal |
| `/topdeal` | Best discount |
| `/search <kw>` | Search products |
| `/referral` | Get invite link + stats |
| `/about` | Bot info |
| `/contact` | Channel link |

## CI/CD Pipeline

GitHub Actions runs every 4 hours:

1. `feeder.py` → regenerate content from products
2. `poster.py` → post 1 deal to channel
3. `referral.py --oneshot` → log referral stats
4. `reporting.py --daily` → send admin report
5. Netlify deploy → update click tracker
6. Commit updated state back to repo

Zero infrastructure cost. GitHub Actions free tier is enough for months.

## What I Learned

**1. Consistency beats volume.** Posting 1 deal every 4 hours outperformed 5 random posts daily. The audience knows when to expect content.

**2. Hinglish content works.** Mixing Hindi and English hooks ("Ghar ki deal chahiye?") increased engagement 3x compared to English-only posts.

**3. Progress bars drive referrals.** Showing users "3/5 friends toward 1.5x points" in /referral increased referral link generation significantly.

**4. Serverless click tracking is cheap.** Netlify's free tier handles thousands of redirects monthly. No database needed — Blob store is enough.

## Getting Started

The full source code is available on Gumroad with a complete setup guide (SETUP.md).

**Includes:**
- 10 Python modules (1,500+ lines)
- 30 sample products with 90 pre-generated content items
- Netlify click tracker with per-product analytics
- GitHub Actions CI/CD workflow
- Setup scripts for Windows (setup.bat) and Linux/Mac (setup.sh)
- 30-minute deploy guide

[https://shaswat7.gumroad.com/l/tg-affiliate-system](https://shaswat7.gumroad.com/l/tg-affiliate-system)

---

*Built with Python 3.12, python-telegram-bot v20, Telethon, GitHub Actions, and Netlify.*
