import os
import requests
from dotenv import load_dotenv

def send_poll_direct():
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = os.getenv("CHANNEL_ID")
    
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": chat_id,
        "question": "Bhaiyo, agla mega loot kya chahiye? (Sasta deal detection mode on!)",
        "options": ["📱 Earphones/TWS", "⌚ Smartwatches", "🔌 USB Cables/Chargers", "🍟 Snacks/Loot Food"],
        "is_anonymous": True,
        "allows_multiple_answers": True
    }
    
    import json
    payload["options"] = json.dumps(payload["options"])
    
    print(f"[*] Sending direct poll to {chat_id}...")
    r = requests.post(url, data=payload)
    if r.status_code == 200:
        print("[OK] Poll sent via Direct API!")
    else:
        print(f"[FAIL] Error: {r.text}")

if __name__ == "__main__":
    send_poll_direct()
