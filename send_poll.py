import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from bot_post import send_automated_poll

async def main():
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = os.getenv("CHANNEL_ID")
    
    bot = Bot(token=BOT_TOKEN)
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    
    print(f"[*] Triggering Engagement Poll in {chat_id}...")
    success = await send_automated_poll(bot, chat_id)
    if success:
        print("[OK] Poll sent successfully!")
    else:
        print("[FAIL] Failed to send poll.")

if __name__ == "__main__":
    asyncio.run(main())
