import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

async def test_connection():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    channel = os.getenv("CHANNEL_ID")
    
    if not token or not channel:
        print("❌ Error: BOT_TOKEN or CHANNEL_ID missing in Environment!")
        return

    bot = Bot(token)
    try:
        chat_id = f"@{channel}" if not channel.startswith("@") else channel
        me = await bot.get_me()
        print(f"✅ Bot Connected: @{me.username}")
        print(f"✅ Bot is ready for {chat_id}!")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
