import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

async def main():
    print("Testing connection...")
    client = TelegramClient('userbot_session', int(API_ID), API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Not authorized. Manual login needed.")
    else:
        print("Authorized!")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
