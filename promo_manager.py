import asyncio
import os
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# List of accounts (Worker Accounts for promotion)
ACCOUNTS = [
    {"phone": os.getenv("PHONE_NUMBER"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
    {"phone": os.getenv("PHONE_NUMBER_2"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
    {"phone": os.getenv("PHONE_NUMBER_3"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
]

# SESSION FILENAMES (Matching your existing files)
SESSION_FILES = ["userbot_session", "worker_2_session", "worker_3_session"]

# Path to the list of groups to promote in
GROUPS_FILE = "verified_promo_groups.txt" # [NEW] Use verified groups first
FALLBACK_GROUPS = "promo_groups_list.txt"

CHANNEL_ID = os.getenv("CHANNEL_ID", "@budgetdeals_india").replace('@', '')

PROMO_MESSAGES = [
    f"""
🛑 **PRICE GLITCH ALERT: ₹1 DEALS DETECTED!** 🚨

Amazon aur Flipkart ke **₹1 Loots** abhi live hain! 😱🔥

Join Fast: https://t.me/{CHANNEL_ID}
Join Fast: https://t.me/{CHANNEL_ID}

*Direct Loot links yahan milti hain!* 🏃‍♂️⏳
""",
    f"""
🛍️ **LOOT ALERT (India's Fastest Deals) 🛍️**

Join now for:
✅ ₹1 Sample Products
✅ 90% OFF Price Glitches
✅ Amazon/Flipkart Hidden Deals

Join: https://t.me/{CHANNEL_ID}
Join: https://t.me/{CHANNEL_ID}

*Skip mat karo, baad mein pachtoge!* 🔥✨
"""
]

async def send_promo_to_group(group, session_name, acc):
    print(f"[*] Post to {group} using {session_name}...")
    try:
        session_map = {
            "userbot_session": "TELEGRAM_SESSION_1",
            "worker_2_session": "TELEGRAM_SESSION_2",
            "worker_3_session": "TELEGRAM_SESSION_3"
        }
        env_key = session_map.get(session_name)
        session_data = os.getenv(env_key) if env_key else None

        if session_data:
            client = TelegramClient(StringSession(session_data), acc["api_id"], acc["api_hash"])
        else:
            client = TelegramClient(session_name, acc["api_id"], acc["api_hash"])
        
        await client.start()
        
        if not await client.is_user_authorized():
            print(f"[!] Session '{session_name}' not authorized.")
            await client.disconnect()
            return False

        msg = random.choice(PROMO_MESSAGES) # [NEW] Random message to avoid spam filters
        await client.send_message(group, msg, link_preview=False)
        print(f"[SUCCESS] Posted in {group}")
        
        await client.disconnect()
        return True
    except Exception as e:
        print(f"[FAILED] Error in {group}: {e}")
        return False

async def main():
    print(f"[*] Starting Promotion Cycle...")
    
    # [NEW] Smart group loading
    if os.path.exists(GROUPS_FILE):
        target_file = GROUPS_FILE
    else:
        target_file = FALLBACK_GROUPS

    if not os.path.exists(target_file):
        print(f"[ERROR] No group list found.")
        return

    with open(target_file, "r") as f:
        groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not groups:
        print("[ERROR] No groups found.")
        return

    active_accounts = [acc for acc in ACCOUNTS if acc["phone"] and acc["api_id"]]
    
    for i, group in enumerate(groups):
        session_name = SESSION_FILES[i % len(SESSION_FILES)]
        acc = active_accounts[i % len(active_accounts)]
        
        success = await send_promo_to_group(group, session_name, acc)
        
        if success:
            delay = random.randint(120, 240) # [NEW] Longer delay for groups to be safer
            print(f"[*] Waiting {delay}s...")
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
