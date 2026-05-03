import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

ACCOUNTS = [
    {"session": "userbot_session", "env": "TELEGRAM_SESSION_1"},
    {"session": "worker_2_session", "env": "TELEGRAM_SESSION_2"},
    {"session": "worker_3_session", "env": "TELEGRAM_SESSION_3"}
]

async def check_account(acc):
    session_data = os.getenv(acc["env"])
    if session_data:
        client = TelegramClient(StringSession(session_data), int(API_ID), API_HASH)
        name = f"StringSession ({acc['env']})"
    else:
        client = TelegramClient(acc["session"], int(API_ID), API_HASH)
        name = f"LocalSession ({acc['session']})"
    
    print(f"[*] Checking {name}...")
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"[OK] Authorized: {me.first_name} (@{me.username})")
        else:
            print(f"[!] NOT Authorized: {name} needs login.")
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
    finally:
        await client.disconnect()

async def main():
    for acc in ACCOUNTS:
        await check_account(acc)
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
