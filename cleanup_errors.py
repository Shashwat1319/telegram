import asyncio
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from telethon import TelegramClient
from telethon.tl.types import Message
from dotenv import load_dotenv

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def main():
    client = TelegramClient('userbot_session', int(API_ID), API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Not authorized.")
        return

    print(f"Cleaning channel {CHANNEL_ID}...")
    to_delete = []
    
    async for message in client.iter_messages(CHANNEL_ID, limit=200):
        if message.text:
            text = message.text.upper()
            if "SYSTEM ERROR" in text or "WAITING FOR ACCESS" in text or "None" in text:
                print(f"[DELETE] ID: {message.id} | Text: {text[:30]}...")
                to_delete.append(message.id)
        elif not message.text and not message.media:
            # Empty messages
            to_delete.append(message.id)

    if to_delete:
        await client.delete_messages(CHANNEL_ID, to_delete)
        print(f"Successfully deleted {len(to_delete)} bad messages.")
    else:
        print("No matches found to delete.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
