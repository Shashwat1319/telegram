# SmartGahr — Telegram Affiliate Automation

**Channel:** `@smartgahr` | **Bot:** `@Ffzon_bot` | **Website:** budgetdealsindia.netlify.app

---

## What It Does

A fully automated Amazon affiliate marketing platform that discovers products, generates promotional content in Hinglish, posts deals to Telegram channels, tracks affiliate clicks, runs an interactive bot, manages referrals, and emails newsletters — all running on GitHub Actions CI/CD and Netlify serverless.

---

## Architecture

```
GitHub Actions (every 4h)
│
├── feeder.py          Product JSON → 3 content variants (pain-fix, deal-alert, short-urgency)
├── poster.py          Posts formatted deal to Telegram channel with inline buttons
├── referral.py        One-shot referral stats
├── reporting.py       Daily admin report with member count
└── Netlify Deploy     Deploys redirector functions

Local Orchestrator (pythonw.exe, auto-start at login)
│
├── bot.py             @Ffzon_bot — /deal /topdeal /search /referral /about /contact
└── referral.py        Event listener — detects joins via Telethon, sends welcome DMs

Netlify Edge Functions
│
├── go.js              Click tracker → 302 redirect + Amazon affiliate tag + per-product analytics
├── stats.js           Daily/grand total click statistics
└── subscribe.js       Email newsletter with Telegram admin notification

Static Website (Astro v6)
│
├── Landing page with deal grid, blog, email signup, Telegram CTA
├── Blog + deal content collections (MDX)
├── RSS feed, XML sitemap, JSON-LD structured data
└── Deployed to budgetdealsindia.netlify.app
```

---

## Modules

| Module | Lines | Role |
|--------|-------|------|
| `orchestrator.py` | 212 | Main loop — runs bot + referral threads with PID locking |
| `bot.py` | 282 | Telegram bot with 7 commands |
| `poster.py` | 198 | Automated channel poster with HTML formatting + dedup |
| `feeder.py` | 197 | Product-to-content converter (3 format variants) |
| `referral.py` | 156 | Referral links + join detection + tiered rewards |
| `reporting.py` | 89 | Daily admin reports + milestone goals |
| `group_poster.py` | 181 | Cross-post deals to Telegram groups |
| `utils.py` | 68 | Shared helpers (tracked_url, esc_md, ASIN extract) |
| `data.py` | 39 | Atomic JSON file I/O |
| `config_loader.py` | 17 | Config with mtime caching |

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **Languages** | Python 3.12, JavaScript, TypeScript |
| **Frameworks** | python-telegram-bot v20, Telethon, Astro v6 |
| **APIs** | Telegram Bot API, Telegram MTProto, Amazon Affiliate (IN) |
| **Cloud** | Netlify (Edge Functions, Blob Store), GitHub Actions CI/CD |
| **Python** | asyncio, aiohttp, pillow, python-dotenv, requests |
| **Storage** | Netlify Blobs, JSON files |

---

## CI/CD Pipeline (GitHub Actions)

Triggered every 4 hours + on push + manually:

1. `feeder.py --source product_home.json` → generates 57 content items
2. `python poster.py` → posts 1 deal to @smartgahr
3. `referral.py --oneshot` → logs referral stats
4. `reporting.py --daily` → sends admin report
5. Netlify deploy → click tracker stays live
6. Commits updated state back to repo

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

## Channel Profile

| Metric | Value |
|--------|-------|
| Name | SmartGahr - Home & Kitchen Deals Under ₹999 |
| Handle | @smartgahr |
| Hashtags | #SmartGahr #HomeUnder999 #KitchenDeals #AmazonHome #GharKiDeal #BudgetHome |
| Content | 57 items (19 products × 3 formats) |
| Posting | Every 4 hours (CI) |
| Click tracking | Per-product via Netlify redirector |

---

*Built by Shashwat — fully automated affiliate marketing.*
