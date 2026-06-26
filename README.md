# 🤖 Budget Deals India — Telegram Automation System
**Channel:** `@budgetdeals_india` | **Bot:** `@Ffzon_bot` | **Goal:** 43 → 5,000+ members + affiliate revenue

---

## 🛠️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  orchestrator.py  (single entrypoint — pythonw, auto-start) │
│  ├── bot_interactive.py     — @Ffzon_bot /start /deal /referral /stats │
│  ├── referral_tracker.py    — detects joins, sends welcome DM      │
│  ├── group_poster.py        — cross-posts deals to 11 groups/2h    │
│  ├── promo_sender.py        — DMs scraped leads every 6h           │
│  ├── channel_announcement.py — pins referral announcement          │
│  ├── daily_report.py        — posts daily stats to channel         │
│  ├── referral_manager.py    — referral links + reward points       │
│  └── bot_post.py            — scheduled channel posts (30 min)     │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Netlify Functions (budgetdeals-tracker.netlify.app)        │
│  ├── go        — click tracking redirect with affiliate tag │
│  └── subscribe — email capture for newsletter               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Current Project Structure

```
D:\Telegram\telegram\
├── orchestrator.py           # Main loop — runs bot + all periodic tasks
├── orchestrator_state.json   # Checkpoint for auto-resume after reboot
├── orchestrator.log          # Runtime logs
├── bot_interactive.py        # @Ffzon_bot handlers
├── referral_tracker.py       # Join detection + welcome DM
├── group_poster.py           # Cross-post to verified_promo_groups.txt
├── promo_sender.py           # DM outreach to leads
├── channel_announcement.py   # Post/pin referral announcement
├── daily_report.py           # Daily stats to channel
├── referral_manager.py       # Referral link gen + tiered rewards
├── bot_post.py               # Scheduled channel deal posts
├── utils.py                  # Shared helpers (tracked_link, prices, etc.)
├── verified_promo_groups.txt # 11 target groups for cross-posting
├── product.json              # Scraped Amazon deals (source of truth)
├── posted_products.json      # Deduplication log
├── referrals.json            # Referral links + join tracking (committed)
├── link_adder.html           # Local UI to add deals
├── netlify-redirector/
│   └── functions/
│       ├── go.js             # Click tracker + affiliate redirect
│       └── subscribe.js      # Email signup endpoint
└── .env                      # All secrets (rotated manually)
```

---

## ⚙️ Tech Stack

| Layer | Tech |
|-------|------|
| Runtime | Python 3.12, Telethon, python-telegram-bot v20 |
| Scheduler | Built-in asyncio loops (no external deps) |
| Click Tracking | Netlify Serverless Functions + Blobs |
| Affiliate | Amazon IN (`shashwat022-21`) / US (`shashwat01-20`) |
| AI Extraction | Gemini API (via `auto_blogger.py` for deal scraping) |
| Persistence | JSON files + Netlify Blobs |
| Auto-start | Windows Startup shortcut → `pythonw.exe orchestrator.py` |

---

## 🔁 Automated Loops (orchestrator.py)

| Task | Interval | Purpose |
|------|----------|---------|
| Bot polling | Continuous | Handle /start /deal /referral /stats |
| Referral tracker | Event-driven | Detect joins, send welcome DM, award points |
| Group poster | Every 2h | Cross-post 1 deal to 11 groups |
| Promo sender | Every 6h | DM scraped leads with deals |
| Daily report | 24h | Post member count, top referrers, clicks |
| Channel post | Every 30m | Auto-post deals to @budgetdeals_india |
| Referral reminder | 4h | Pin reminder in channel |

---

## 📊 Day 2 Baseline (Jun 25)

| Metric | Value |
|--------|-------|
| Channel members | 43 |
| Referral links created | 104 |
| Referral joins | 0 |
| Groups in rotation | 11 |
| Orchestrator uptime | ~1h (restarted for fixes) |

---

## 🚀 Next Level Checklist

- [ ] Post referral CTA in channel daily (Task 1)
- [ ] Add 2 groups/day to `verified_promo_groups.txt`
- [ ] Wire `auto_blogger.py` → cron to refresh `product.json` daily
- [ ] Build `goal_tracker.py` → show progress bar in daily report
- [ ] Set up Netlify Blobs dashboard for click analytics
- [ ] Add UTM params to tracked links for Google Analytics

---

*Built by Shashwat — automation that earns while you sleep.*