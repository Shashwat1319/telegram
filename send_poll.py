import asyncio
import os
import sys
from telegram import Bot
from dotenv import load_dotenv

async def send_custom_poll():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    
    if not token or not channel_id:
        print("[ERROR] Missing BOT_TOKEN or CHANNEL_ID in .env")
        return

    bot = Bot(token=token)
    
    # Default poll configuration
    question = "Bhaiyo, aapko sabse zyada deals kis category mein chahiye? 🔥"
    options = [
        "📱 Mobiles & Accessories",
        "👟 Shoes & Fashion",
        "🎧 Earphones & Gadgets",
        "🏠 Kitchen & Home Appliances",
        "🧴 Beauty & Personal Care"
    ]

    try:
        print(f"[*] Sending Poll to {channel_id}...")
        await bot.send_poll(
            chat_id=channel_id,
            question=question,
            options=options,
            is_anonymous=True, # Channels only support anonymous polls
            allows_multiple_answers=True
        )
        print("[SUCCESS] Poll sent successfully! check your channel.")
    except Exception as e:
        print(f"[FAILED] Could not send poll: {e}")

if __name__ == "__main__":
    asyncio.run(send_custom_poll())
