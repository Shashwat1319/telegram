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
GROUPS_FILE = "promo_groups_list.txt"
CHANNEL_ID = os.getenv("CHANNEL_ID", "@budgetdeals_india").replace('@', '')

PROMO_MESSAGE = f"""
🛑 **LOOT SYSTEM ERROR: ₹1 DEALS DETECTED!** 🚨

Abhi tak join nahi kiya? Amazon aur Flipkart par **₹1 Loots** aur **Price Glitch** links sirf yahan post ho rahi hain! 😱

🔥 **JOIN FAST (Link valid for 5 mins):** https://t.me/{CHANNEL_ID}
🔥 **JOIN FAST:** https://t.me/{CHANNEL_ID}

🏃‍♂️ *Jaldi karo, link kabhi bhi expire ho sakta hai! Sab loot rahe hain!* ⏳
"""

async def send_promo_to_group(group, session_name, acc):
    print(f"[*] Connecting with session '{session_name}' to post in {group}...")
    try:
        # [NEW] Prefer String Session from Environment (for GitHub Actions)
        session_map = {
            "userbot_session": "TELEGRAM_SESSION_1",
            "worker_2_session": "TELEGRAM_SESSION_2",
            "worker_3_session": "TELEGRAM_SESSION_3"
        }
        env_key = session_map.get(session_name)
        session_data = os.getenv(env_key) if env_key else None

        if session_data:
            print(f"[*] Using String Session from environment ({env_key}).")
            client = TelegramClient(
                StringSession(session_data),
                acc["api_id"],
                acc["api_hash"]
            )
        else:
            # Use client.start() which is more robust for existing sessions
            client = TelegramClient(session_name, acc["api_id"], acc["api_hash"])
        
        await client.start()
        
        if not await client.is_user_authorized():
            print(f"[!] Session '{session_name}' is not authorized. Skipping...")
            await client.disconnect()
            return False

        await client.send_message(group, PROMO_MESSAGE, link_preview=False)
        print(f"[SUCCESS] Promo sent to {group} using {session_name}")
        
        await client.disconnect()
        return True
    except Exception as e:
        print(f"[FAILED] Could not post to {group} with {session_name}: {e}")
        return False

async def main():
    print(f"[*] Starting Mission 200: Promotion Cycle for @{CHANNEL_ID}...")
    
    if not os.path.exists(GROUPS_FILE):
        print(f"[ERROR] {GROUPS_FILE} not found.")
        return

    with open(GROUPS_FILE, "r") as f:
        groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not groups:
        print("[ERROR] No groups found.")
        return

    # Filter out empty accounts
    active_accounts = [acc for acc in ACCOUNTS if acc["phone"] and acc["api_id"]]
    
    for i, group in enumerate(groups):
        session_name = SESSION_FILES[i % len(SESSION_FILES)]
        acc = active_accounts[i % len(active_accounts)]
        
        # Execute the promo send
        success = await send_promo_to_group(group, session_name, acc)
        
        if success:
            # Safe sleep variable (60-120 seconds) to prevent account bans
            delay = random.randint(60, 120)
            print(f"[*] Safe Mode: Waiting {delay}s before next post...")
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(5) # Short sleep if failed

if __name__ == "__main__":
    asyncio.run(main())
