import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

# Load configuration
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

ACCOUNTS = [
    {"session": "userbot_session", "phone": os.getenv("PHONE_NUMBER")},
    {"session": "worker_2_session", "phone": os.getenv("PHONE_NUMBER_2")},
    {"session": "worker_3_session", "phone": os.getenv("PHONE_NUMBER_3")}
]

async def authorize_account(account):
    session_name = account["session"]
    phone = account["phone"]
    
    if not phone:
        print(f"\n[!] Skipping {session_name}: No phone number in .env")
        return

    print(f"\n{'='*50}")
    print(f"Checking Account: {phone} ({session_name})")
    print(f"{'='*50}")

    client = TelegramClient(session_name, int(API_ID), API_HASH)
    
    try:
        await client.start(phone=phone)
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"[SUCCESS] {phone} is AUTHORIZED as {me.first_name}")
        else:
            print(f"[FAILED] {phone} could not be authorized.")
    except Exception as e:
        print(f"[ERROR] {phone} failed: {e}")
    finally:
        await client.disconnect()

async def main():
    print("--- Telegram Session Fixer ---")
    print("This script will ensure all 3 accounts are logged in.")
    print("If an account needs an OTP, it will ask you here.")
    
    for acc in ACCOUNTS:
        await authorize_account(acc)
    
    print("\nAll accounts checked! You can now run your main scripts.")

if __name__ == "__main__":
    asyncio.run(main())
