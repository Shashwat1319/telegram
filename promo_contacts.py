import asyncio
import os
import random
import json
from datetime import datetime, timedelta
from telethon import TelegramClient
from dotenv import load_dotenv

# Load credentials
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Promo message from user requirements
PROMO_MESSAGE = f"""
🛑 **LOOT SYSTEM ERROR: ₹1 DEALS DETECTED!** 🚨

Abhi tak join nahi kiya? Amazon aur Flipkart par **₹1 Loots** aur **Price Glitch** links sirf yahan post ho rahi hain! 😱

🔥 **JOIN FAST:** https://t.me/{CHANNEL_ID.replace('@','')}
"""

ACCOUNTS = [
    {"session": "userbot_session"},
    {"session": "worker_2_session"},
    {"session": "worker_3_session"}
]

HISTORY_FILE = "promo_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

async def send_promo(account_session, contact):
    client = TelegramClient(account_session, int(API_ID), API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"Skipping {account_session}: Not authorized.")
            return

        print(f"[*] Sending promo to {contact} via {account_session}...")
        await client.send_message(contact, PROMO_MESSAGE, link_preview=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to message {contact}: {e}")
        return False
    finally:
        await client.disconnect()

async def main():
    history = load_history()
    now = datetime.now()
    
    for account in ACCOUNTS:
        session = account["session"]
        filename = f"contacts_{session}.txt"
        
        if not os.path.exists(filename):
            print(f"Skipping {session}: {filename} not found.")
            continue
            
        with open(filename, "r") as f:
            contacts = [line.strip() for line in f if line.strip()]
            
        for contact in contacts:
            # Check weekly limit
            last_sent = history.get(contact)
            if last_sent:
                last_sent_dt = datetime.fromisoformat(last_sent)
                if now - last_sent_dt < timedelta(days=7):
                    # print(f"Skipping {contact}: Already messaged this week.")
                    continue
            
            # Send Promo
            success = await send_promo(session, contact)
            if success:
                history[contact] = now.isoformat()
                save_history(history)
                # Strict delay to avoid bans (30-60s)
                wait_time = random.randint(45, 90)
                print(f"Waiting {wait_time}s to avoid spam flag...")
                await asyncio.sleep(wait_time)

if __name__ == "__main__":
    asyncio.run(main())
