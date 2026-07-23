# Telegram Affiliate Automation — Setup Guide

## What You're Getting

A fully automated system that:
- Generates promotional content from product data (3 formats per product)
- Posts deals to your Telegram channel every 4 hours via GitHub Actions
- Runs an interactive bot with 7 commands (/deal, /topdeal, /search, /referral, /about, /contact)
- Tracks affiliate clicks via Netlify serverless redirector
- Detects new members and sends welcome DMs with referral rewards
- Sends daily admin reports with member count and referral stats
- Zero manual work after setup

---

## Prerequisites

| Item | How to get it | Cost |
|------|--------------|------|
| GitHub account | github.com/signup | Free |
| Telegram Bot Token | Message @BotFather on Telegram | Free |
| Telegram API ID + Hash | my.telegram.org/apps | Free |
| Telegram Channel | Create on Telegram, add bot as admin | Free |
| Amazon Associates ID | affiliate-program.amazon.in | Free |
| Netlify account | netlify.com/signup | Free |

---

## Step 1: Set Up Secrets on GitHub

Your project uses **GitHub Actions** to post deals and run reports. Secrets are stored in your repo.

### 1a. Push the code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### 1b. Create a GitHub Environment

1. Go to your repo → Settings → Environments
2. Click **New environment**
3. Name it `telegram`
4. Add these secrets:

| Secret | Value |
|--------|-------|
| `BOT_TOKEN` | Your bot token from @BotFather |
| `API_ID` | From my.telegram.org |
| `API_HASH` | From my.telegram.org |
| `ADMIN_CHAT_ID` | Your Telegram user ID (get from @userinfobot) |
| `TELEGRAM_SESSION_1` | Session string (see 1c below) |
| `NETLIFY_AUTH_TOKEN` | From Netlify user settings → Personal access tokens |
| `NETLIFY_SITE_ID` | Your Netlify site API ID |

### 1c. Generate Telegram Session String

The bot needs a Telethon session string to detect new members joining your channel.

```bash
pip install telethon
python -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = YOUR_API_ID
api_hash = 'YOUR_API_HASH'

with TelegramClient(StringSession(), api_id, api_hash) as client:
    client.send_message('me', 'Session: ' + client.session.save())
    print('Check your Telegram saved messages')
"
```

Copy the session string from your Telegram Saved Messages and add it as `TELEGRAM_SESSION_1` in GitHub secrets.

---

## Step 2: Add Bot to Channel

1. Add your bot as **admin** to your Telegram channel
2. Give it these permissions:
   - Post messages
   - Edit messages
   - Delete messages
   - Pin messages
   - Manage invites (required for referral links)

---

## Step 3: Configure local files

### 3a. Copy config template

```bash
copy config.example.json config.json
# or on Linux:
cp config.example.json config.json
```

Edit `config.json` and replace:
- `username` → your bot username
- `channel_id` → your channel (e.g., @mydeals)
- `channel_handle` → your channel handle (without @)
- `welcome_message` → your welcome text
- `hashtags` → your channel hashtags

### 3b. Create .env (for local testing)

```bash
copy .env.example .env
# or on Linux:
cp .env.example .env
```

Fill in your real values.

---

## Step 4: Set Up Netlify Click Tracker

The redirector tracks every click on your affiliate links.

### 4a. Deploy to Netlify

Option A — Via GitHub Actions (recommended):
- The CI pipeline auto-deploys `netlify-redirector/` to Netlify on every push
- You need `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` in GitHub secrets

Option B — Manual deploy:
1. Go to netlify.com → Sites → Add new site → Deploy manually
2. Drag-and-drop the `netlify-redirector/` folder
3. Copy your site URL (e.g., `https://your-site.netlify.app`)

### 4b. Update click tracker URL

In your GitHub secrets, set `CLICK_TRACKER_URL` to your Netlify site URL.

### 4c. Verify it works

Visit `https://your-site.netlify.app/.netlify/functions/go?id=test&link=https://amazon.in`
It should redirect you to Amazon with your affiliate tag.

---

## Step 5: Run Locally (Optional)

For local testing before the CI pipeline takes over:

```bash
pip install -r requirements.txt

# Generate content from products
python feeder.py --source product_home.json --output content_home.json

# Post a deal to your channel
python poster.py

# Run the bot interactively
python orchestrator.py
```

---

## Step 6: Let CI Run Automatically

Your pipeline is already configured to:
- Run every 4 hours
- Generate fresh content
- Post 1 deal to your channel
- Log referral stats
- Send admin report
- Deploy Netlify redirector
- Commit updated state to repo

Monitor runs: GitHub → Your repo → Actions tab

---

## Customizing Products

Edit `product_home.json`:
```json
{
  "products": [
    {
      "name": "Your Product Name",
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

Then regenerate content:
```bash
python feeder.py --source product_home.json --output content_home.json
```

---

## Commands Your Bot Will Respond To

| Command | What it does |
|---------|-------------|
| `/start` | Welcome message with channel link |
| `/deal` | Random unposted deal |
| `/topdeal` | Highest discount deal |
| `/search <keyword>` | Search deals by title |
| `/referral` | Generate invite link + stats |
| `/about` | Bot description |
| `/contact` | Channel link |

---

## File Structure

```
├── bot.py                  # Interactive bot (7 commands)
├── feeder.py               # Converts products → content in 3 formats
├── poster.py               # Posts deals to Telegram channel
├── referral.py             # Referral links + join detection + rewards
├── reporting.py            # Daily reports + milestone goals
├── orchestrator.py         # Main loop (bot + referral tracker)
├── group_poster.py         # Cross-post deals to Telegram groups
├── utils.py                # Shared helpers
├── data.py                 # JSON file operations
├── config_loader.py        # Config with caching
├── config.json             # Your configuration
├── config.example.json     # Template config
├── .env.example            # Template environment variables
├── requirements.txt        # Python dependencies
├── product_home.json       # Your products (sample included)
├── content_home.json       # Generated content (72 items included)
├── SETUP.md                # This file
├── netlify-redirector/
│   ├── functions/
│   │   ├── go.js           # Click tracker + affiliate redirect
│   │   └── subscribe.js    # Email signup endpoint
│   └── netlify.toml
└── .github/workflows/
    └── update_products.yml # CI/CD pipeline (every 4h)
```

---

## Troubleshooting

**Bot doesn't respond to commands**
- Check `BOT_TOKEN` is correct in `.env`
- Make sure the bot is not stopped (message @BotFather → /mybots → select bot → Bot Settings → Group Privacy → Disable)

**CI pipeline fails**
- Check GitHub Secrets are all filled correctly
- Go to Actions tab → click failed run → check which step failed

**No deals appearing in channel**
- Check `channel_posting` is `enabled: true` in `config.json`
- Verify bot is admin in your channel
- Check CI run logs for poster.py errors

**Referral links not working**
- Bot must have "Manage invites" permission in the channel
- Check `TELEGRAM_SESSION_1` is a valid session string

**Need help?** Open an issue on GitHub or contact me.
