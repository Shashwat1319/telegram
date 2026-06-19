import requests, os, json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

def get_stats():
    if not CLICK_TRACKER_URL: return None
    try: return requests.get(f"{CLICK_TRACKER_URL}/stats").json()
    except: return None

def get_member_count():
    if not BOT_TOKEN: return "N/A"
    try:
        cid = os.getenv("CHANNEL_ID")
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={cid}")
        return r.json().get("result", "N/A") if r.status_code == 200 else "N/A"
    except: return "N/A"

def send_telegram(msg):
    if not BOT_TOKEN or not ADMIN_CHAT_ID: return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    stats = get_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    clicks_today = stats["history"].get(today, 0) if stats and "history" in stats else 0
    total_clicks = stats.get("total_clicks", 0) if stats else 0
    est_sales = round(clicks_today * 0.05) if isinstance(clicks_today, (int, float)) else 0
    members = get_member_count()

    product_count = img_count = 0
    if os.path.exists("product.json"):
        try:
            prods = json.load(open("product.json", encoding="utf-8"))["products"]
            product_count = len(prods)
            img_count = sum(1 for p in prods if p.get('image'))
        except: pass

    fb_today = ig_today = 0
    if os.path.exists("content_scheduler_log.json"):
        try:
            log = json.load(open("content_scheduler_log.json"))
            for entry in log.get(today, []):
                if entry["platform"] == "facebook" and entry["status"] == "posted": fb_today += 1
                if entry["platform"] == "instagram" and entry["status"] == "posted": ig_today += 1
        except: pass

    report = f"""🚀 **DAILY REPORT** ({today})

👥 **Members**: {members}
📦 **Deals Queue**: {product_count} ({img_count} with images)
👆 **Clicks Today**: {clicks_today}
📈 **Total Clicks**: {total_clicks}
💰 **Est. Sales**: {est_sales}
📘 **FB Posts**: {fb_today}
📸 **IG Posts**: {ig_today}

---
*Target: ₹3000/day ≈ 600 clicks/day*
*Run 'py -3 trending_updater.py' to refresh deals with images*"""
    print(report)
    send_telegram(report)

if __name__ == "__main__":
    main()
