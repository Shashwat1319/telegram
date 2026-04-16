import asyncio
import os
import random
import json
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load credentials
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Polite and respectful promo message for family/personal contacts
PROMO_MESSAGE = f"""
Hi! 👋 

Agar aapko online shopping karna pasand hai aur aap Amazon/Flipkart par paise bachana chahte hain, toh maine ek naya Telegram channel shuru kiya hai wahan main daily best discounts aur offers share karta hoon. 🎁

Aap yahan join kar sakte hain: https://t.me/{CHANNEL_ID.replace('@','')}

Thank you! 🙏✨
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

async def send_promo(client, account_session, contact):
    try:
        if not await client.is_user_authorized():
            print(f"Skipping {account_session}: Not authorized.")
            return False

        print(f"[*] Sending promo to {contact} via {account_session}...")
        await client.send_message(contact, PROMO_MESSAGE, link_preview=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to message {contact}: {e}")
        return False

def get_client(account_session):
    # Mapping session filename to Env Variable
    session_map = {
        "userbot_session": "TELEGRAM_SESSION_1",
        "worker_2_session": "TELEGRAM_SESSION_2",
        "worker_3_session": "TELEGRAM_SESSION_3"
    }
    env_key = session_map.get(account_session)
    session_data = os.getenv(env_key) if env_key else None

    if session_data:
        return TelegramClient(StringSession(session_data), int(API_ID), API_HASH)
    else:
        return TelegramClient(account_session, int(API_ID), API_HASH)

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
            
        client = get_client(session)
        await client.connect()
        
        try:
            for contact in contacts:
                # Check weekly limit
                last_sent = history.get(contact)
                if last_sent:
                    last_sent_dt = datetime.fromisoformat(last_sent)
                    if now - last_sent_dt < timedelta(days=7):
                        continue
                
                # Send Promo using the open client
                success = await send_promo(client, session, contact)
                if success:
                    history[contact] = now.isoformat()
                    save_history(history)
                    # Strict delay to avoid bans (30-60s)
                    wait_time = random.randint(45, 90)
                    print(f"Waiting {wait_time}s to avoid spam flag...")
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(10) # Small wait if failed to not hammer the API
        finally:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
