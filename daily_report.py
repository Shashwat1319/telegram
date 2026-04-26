import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

def get_stats():
    if not CLICK_TRACKER_URL:
        return None
    try:
        r = requests.get(f"{CLICK_TRACKER_URL}/stats")
        return r.json()
    except:
        return None

def send_telegram(message):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def main():
    stats = get_stats()
    date_today = datetime.now().strftime("%Y-%m-%d")
    
    clicks_today = 0
    if stats and "history" in stats:
        clicks_today = stats["history"].get(date_today, 0)
        total_clicks = stats.get("total_clicks", 0)
    else:
        clicks_today = "N/A"
        total_clicks = "N/A"

    # Count leads
    leads_count = 0
    if os.path.exists("scraped_leads.txt"):
        with open("scraped_leads.txt", "r") as f:
            leads_count = len(f.readlines())

    report = f"""
🚀 **DAILY PROGRESS REPORT** ({date_today})

✅ **Clicks Today**: {clicks_today}
📈 **Total Clicks**: {total_clicks}
👥 **Leads in Database**: {leads_count}

---
💡 *Status*: Orchestrator is running 24/7. 
*Target*: $50/day (Approx. 400+ Clicks/day needed)

Keep going, we are scaling! 🔥
"""
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode('ascii', 'ignore').decode('ascii'))
    send_telegram(report)

if __name__ == "__main__":
    main()
