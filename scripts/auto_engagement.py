import asyncio
import os
import random
from telegram import Bot
from dotenv import load_dotenv

# Re-using the logic from bot_post but as a standalone script
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def send_poll():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("[ERROR] BOT_TOKEN or CHANNEL_ID missing.")
        return

    async with Bot(token=BOT_TOKEN) as bot:
        chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID

        questions = [
            {
                "q": "Bhaiyo, aaj kis category mein sabse zyada deals chahiye? 🔥",
                "opts": ["📱 Mobiles & Accessories", "👟 Shoes & Fashion", "🎧 Gadgets", "🏠 Home & Kitchen"]
            },
            {
                "q": "Kya aapne aaj ki top loot deal dekhi? 😱",
                "opts": ["Haan bhai, le li! ✅", "Abhi dekh raha hoon", "Nahi mili bhai", "Budget kam hai abhi"]
            },
            {
                "q": "Next Mega Sale kab shuru karni hai? 🕒",
                "opts": ["Abhi turant!", "Aaj shaam 6 baje", "Kal subah", "Weekend par"]
            }
        ]

        poll = random.choice(questions)
        
        try:
            print(f"[*] Sending Engagement Poll to {chat_id}...")
            await bot.send_poll(
                chat_id=chat_id,
                question=poll["q"],
                options=poll["opts"],
                is_anonymous=True,
                allows_multiple_answers=False
            )
            print("[SUCCESS] Poll sent.")
        except Exception as e:
            print(f"[ERROR] Failed to send poll: {e}")

if __name__ == "__main__":
    asyncio.run(send_poll())
