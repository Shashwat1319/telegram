import asyncio
import os
from telethon import TelegramClient
from telethon.network import ConnectionTcpObfuscated
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = TelegramClient(
        'userbot_session', 
        int(os.getenv('API_ID')), 
        os.getenv('API_HASH'),
        connection=ConnectionTcpObfuscated
    )
    await client.start()
    print("--- 10 Latest Messages from @budgetdeals_india ---")
    async for message in client.iter_messages('@budgetdeals_india', limit=10):
        print(f"ID: {message.id} | Date: {message.date} | Text: {str(message.text)[:50]}...")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
