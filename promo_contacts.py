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

# PROMO MESSAGE
# [NEW] More aggressive but respectful message for high conversion
PROMO_MESSAGE = f"""
Bhai, Amazon/Flipkart se shopping karte ho? 🛍️

Maine ek channel banaya hai jahan daily **Verified Loots**, **Price Drops** aur **90% OFF Deals** milti hain. 😱🔥

Join karlo, extra paisa kyu dena:
👉 https://t.me/{CHANNEL_ID.replace('@','')}

Aaj hi ek ₹149 wali deal miss ho gayi, abhi join karo aur agali miss mat karna! 🙏✨
"""

ACCOUNTS = [
    {"session": "userbot_session"},
    {"session": "worker_2_session"},
    {"session": "worker_3_session"}
]

HISTORY_FILE = "promo_history.json"
LEADS_FILE = "scraped_leads.txt"

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
    
    # [NEW] Prioritize scraped leads, then fallback to contacts
    all_contacts = []
    
    # Load Scraped Leads
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            scraped = [line.strip() for line in f if line.strip()]
            all_contacts.extend(scraped)
            print(f"[*] Loaded {len(scraped)} scraped leads.")

    # Load Account Contacts (optional fallback)
    for account in ACCOUNTS:
        session = account["session"]
        filename = f"contacts_{session}.txt"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                ac_contacts = [line.strip() for line in f if line.strip()]
                all_contacts.extend(ac_contacts)
    
    # Remove duplicates but keep order
    seen = set()
    all_contacts = [x for x in all_contacts if not (x in seen or seen.add(x))]

    if not all_contacts:
        print("[!] No leads found in scraped_leads.txt or contact files.")
        return

    # Round-robin accounts to spread the load
    for i, contact in enumerate(all_contacts):
        # Check weekly limit
        last_sent = history.get(contact)
        if last_sent:
            # Handle both old (string) and new (dict) formats
            ts = last_sent["time"] if isinstance(last_sent, dict) else last_sent
            last_sent_dt = datetime.fromisoformat(ts)
            if now - last_sent_dt < timedelta(days=7):
                continue

        # Select account
        acc_idx = i % len(ACCOUNTS)
        session = ACCOUNTS[acc_idx]["session"]
        
        client = get_client(session)
        try:
            await client.connect()
            success = await send_promo(client, session, contact)
            if success:
                # [FIX] Store detailed history for reporting
                history[contact] = {
                    "time": datetime.now().isoformat(),
                    "account": session
                }
                save_history(history)
                
                # Strict delay to avoid bans (60-120s)
                wait_time = random.randint(60, 120)
                print(f"Waiting {wait_time}s to avoid spam flag...")
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(10)
        finally:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
