import asyncio
import os
import random
import time
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# List of accounts (Worker Accounts for promotion)
ACCOUNTS = [
    {"phone": os.getenv("PHONE_NUMBER"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
    {"phone": os.getenv("PHONE_NUMBER_2"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
    {"phone": os.getenv("PHONE_NUMBER_3"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
]

# Path to the list of groups to promote in
GROUPS_FILE = "promo_groups_list.txt"
CHANNEL_ID = os.getenv("CHANNEL_ID", "@budgetdeals_india").replace('@', '')

PROMO_MESSAGE = f"""
🛑 **LOOT ALERT: SYSTEM GLITCH DETECTED!** 🚨

Bhaiyo, Amazon/Flipkart ke ₹1 Loot deals aur Hidden Error Prices sirf yahan milte hain! 😱

🔥 **Abhi Join Karo:** https://t.me/{CHANNEL_ID}
🔥 **Abhi Join Karo:** https://t.me/{CHANNEL_ID}

🏃‍♂️ *Stock khatam hone se pehle loot lo! Channel link delete hone wala hai!* ⏳
"""

async def run_promotion():
    print(f"[*] Starting Promotion Cycle for @{CHANNEL_ID}...")
    
    if not os.path.exists(GROUPS_FILE):
        print(f"[ERROR] {GROUPS_FILE} not found. Please create it and add group links.")
        return

    with open(GROUPS_FILE, "r") as f:
        groups = [line.strip() for line in f if line.strip()]

    if not groups:
        print("[ERROR] No groups found in promo_groups_list.txt")
        return

    # Filter out empty accounts
    active_accounts = [acc for acc in ACCOUNTS if acc["phone"] and acc["api_id"]]
    
    if not active_accounts:
        print("[ERROR] No active worker accounts found in .env")
        return

    for i, group in enumerate(groups):
        # Rotate accounts to avoid spam filters
        acc = active_accounts[i % len(active_accounts)]
        phone = acc["phone"]
        
        print(f"[*] Post {i+1}/{len(groups)}: Using {phone} for {group}...")
        
        try:
            client = TelegramClient(f'session_{phone.replace("+","")}', acc["api_id"], acc["api_hash"])
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"[!] Account {phone} is not authorized. Skipping...")
                await client.disconnect()
                continue

            # Send the promo message
            await client.send_message(group, PROMO_MESSAGE, link_preview=False)
            print(f"[SUCCESS] Promo sent to {group}")
            
            await client.disconnect()
            
            # Safe sleep variable (30-90 seconds) to prevent account bans
            delay = random.randint(30, 90)
            print(f"[*] Sleeping for {delay}s...")
            await asyncio.sleep(delay)
            
        except Exception as e:
            print(f"[FAILED] Could not post to {group}: {e}")

if __name__ == "__main__":
    asyncio.run(run_promotion())
