import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Pick a few groups to check
GROUPS_TO_CHECK = [
    "@LootDealsDiscussion",
    "@onlinelootrjgroup",
    "@deals_groups"
]

async def check_visibility():
    session_data = os.getenv("TELEGRAM_SESSION_1")
    client = TelegramClient(StringSession(session_data), int(API_ID), API_HASH)
    
    await client.connect()
    print("--- Message Visibility Audit ---")
    
    for group in GROUPS_TO_CHECK:
        print(f"\n[*] Checking group: {group}")
        try:
            # Check last 20 messages to see if OUR promo is there
            async for message in client.iter_messages(group, limit=20):
                text = str(message.text) if message.text else ""
                # Check if it contains our channel link or keywords
                if "t.me/budgetdeals_india" in text or "LOOT ALERT" in text:
                    print(f"[FOUND] Our message is VISIBLE! ID: {message.id} | Date: {message.date}")
                    break
            else:
                print(f"[MISSING] Our message is NOT found in the last 20 messages of {group}.")
        except Exception as e:
            print(f"[ERROR] Could not check {group}: {e}")
            
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(check_visibility())
