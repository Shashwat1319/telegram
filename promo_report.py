import requests, os, json, logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
HISTORY_FILE = "promo_history.json"


def send_telegram(message):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            log.error("Telegram API failed: %s", response.text)
        else:
            log.info("Report sent to Admin.")
    except Exception as e:
        log.error("Failed to send report: %s", e)


def main():
    if not os.path.exists(HISTORY_FILE):
        log.warning("No history file found.")
        return

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        log.error("Failed to load history: %s", e)
        return

    now = datetime.now()
    thirty_mins_ago = now - timedelta(minutes=30)

    recent_sends = []
    for contact, data in history.items():
        # Handle both old (string) and new (dict) formats
        try:
            ts = data["time"] if isinstance(data, dict) else data
            acc = data["account"] if isinstance(data, dict) else "Unknown (Old)"

            send_time = datetime.fromisoformat(ts)
            if send_time > thirty_mins_ago:
                recent_sends.append({
                    "name": contact,
                    "account": acc,
                    "time": send_time.strftime("%H:%M:%S")
                })
        except Exception as e:
            log.debug("Skipping entry %s: %s", contact, e)
            continue

    if not recent_sends:
        send_telegram("🕒 **Promo Report (Last 30m)**: No messages sent in this window.")
        return

    report = f"📊 **PROMO REPORT (Last 30m)**\n\nTotal Sent: {len(recent_sends)}\n\n"
    for s in recent_sends:
        report += f"👤 `{s['name']}`\n🤖 Account: `{s['account']}`\n🕒 Time: `{s['time']}`\n\n"

    # Split if too long
    if len(report) > 4000:
        report = report[:3900] + "\n\n... (too many to list)"

    send_telegram(report)


if __name__ == "__main__":
    main()