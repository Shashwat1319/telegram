import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("BOT_TOKEN or CHANNEL_ID not found in .env")
        return
    
    bot = Bot(token=BOT_TOKEN)
    chat_id = CHANNEL_ID if CHANNEL_ID.startswith("-100") or CHANNEL_ID.startswith("@") else f"@{CHANNEL_ID}"
    
    photo_path = "channel_logo.png"
    if not os.path.exists(photo_path):
        print(f"Photo not found at {photo_path}")
        return
        
    print(f"Uploading Telegram Channel Photo to {chat_id}...")
    try:
        with open(photo_path, 'rb') as photo_file:
            await bot.set_chat_photo(chat_id=chat_id, photo=photo_file)
        print("[SUCCESS] Telegram Channel Photo updated successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to update Telegram photo: {e}")

if __name__ == "__main__":
    asyncio.run(main())
