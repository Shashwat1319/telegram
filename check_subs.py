import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

async def main():
    token = os.getenv("BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    
    if not token or not channel_id:
        print("Error: Missing BOT_TOKEN or CHANNEL_ID in .env")
        return
        
    bot = Bot(token=token)
    try:
        count = await bot.get_chat_member_count(channel_id)
        print(f"TOTAL_SUBSCRIBERS: {count}")
    except Exception as e:
        print(f"Error checking subscribers: {e}")

if __name__ == "__main__":
    asyncio.run(main())
