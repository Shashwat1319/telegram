import asyncio
import os
import random
from telethon import TelegramClient
from telethon.tl.functions.contacts import GetContactsRequest
from dotenv import load_dotenv

# Load credentials
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

ACCOUNTS = [
    {"session": "userbot_session", "phone": os.getenv("PHONE_NUMBER")},
    {"session": "worker_2_session", "phone": os.getenv("PHONE_NUMBER_2")},
    {"session": "worker_3_session", "phone": os.getenv("PHONE_NUMBER_3")}
]

async def fetch_contacts(account):
    session_name = account["session"]
    phone = account["phone"]
    
    if not phone:
        print(f"Skipping {session_name}: No phone number found in .env")
        return

    print(f"\n--- Fetching Contacts for: {phone} ({session_name}) ---")
    client = TelegramClient(session_name, int(API_ID), API_HASH)
    
    try:
        await client.start(phone=phone)
        contacts = await client(GetContactsRequest(hash=0))
        
        filename = f"contacts_{session_name}.txt"
        count = 0
        
        with open(filename, "w", encoding="utf-8") as f:
            for user in contacts.users:
                if user.username:
                    f.write(f"@{user.username}\n")
                    count += 1
                elif user.phone:
                    f.write(f"+{user.phone}\n")
                    count += 1
        
        print(f"[OK] Saved {count} contacts to {filename}")
        
    except Exception as e:
        print(f"[ERROR] Failed for {phone}: {e}")
    finally:
        await client.disconnect()

async def main():
    for acc in ACCOUNTS:
        await fetch_contacts(acc)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
