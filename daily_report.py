import requests, os, json, logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


def get_stats():
    if not CLICK_TRACKER_URL:
        return None
    try:
        r = requests.get(f"{CLICK_TRACKER_URL}/stats", timeout=10)
        if r.status_code == 200:
            return r.json()
        log.warning("Stats API returned %d", r.status_code)
    except Exception as e:
        log.warning("Stats API error: %s", e)
    return None


def get_member_count():
    if not BOT_TOKEN:
        return "N/A"
    try:
        cid = os.getenv("CHANNEL_ID")
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={cid}", timeout=10)
        if r.status_code == 200:
            return r.json().get("result", "N/A")
    except Exception as e:
        log.warning("Member count API error: %s", e)
    return "N/A"


def send_telegram(msg):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        if r.status_code != 200:
            log.error("Telegram API failed: %s", r.text)
        else:
            log.info("Report sent to Admin.")
    except Exception as e:
        log.error("Failed to send report: %s", e)


def main():
    stats = get_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    clicks_today = 0
    total_clicks = 0
    if stats:
        if isinstance(stats.get("history"), dict):
            clicks_today = stats["history"].get(today, 0) or 0
        total_clicks = stats.get("total_clicks", 0) or 0

    est_sales = 0
    if isinstance(clicks_today, (int, float)):
        est_sales = round(clicks_today * 0.05)

    members = get_member_count()

    product_count = img_count = 0
    if os.path.exists("product.json"):
        try:
            prods = json.load(open("product.json", encoding="utf-8")).get("products", [])
            product_count = len(prods)
            img_count = sum(1 for p in prods if p.get('image'))
        except Exception as e:
            log.warning("Failed to load product.json: %s", e)

    fb_today = ig_today = 0
    if os.path.exists("content_scheduler_log.json"):
        try:
            log_data = json.load(open("content_scheduler_log.json"))
            for entry in log_data.get(today, []):
                if entry.get("platform") == "facebook" and entry.get("status") == "posted":
                    fb_today += 1
                if entry.get("platform") == "instagram" and entry.get("status") == "posted":
                    ig_today += 1
        except Exception as e:
            log.warning("Failed to load scheduler log: %s", e)

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
*Add new deals via link_adder.py or edit product.json directly*"""
    log.info("Report sent: members=%s, clicks=%d", members, clicks_today)
    send_telegram(report)


if __name__ == "__main__":
    main()