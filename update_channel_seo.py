import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def update_seo():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Error: BOT_TOKEN or CHANNEL_ID not found in .env")
        return

    # High-traffic SEO targeting keywords
    NEW_NAME = "Amazon Loot Deals - Glitch & Error Prices \U0001f6cd\ufe0f"
    NEW_BIO = (
        "India's #1 channel for Amazon Glitches, Loot Deals & 99 Store offers. "
        "Sasta shopping starts here! \U0001f680 Join & Share for secret deals."
    )

    bot = Bot(token=BOT_TOKEN)
    chat_id = CHANNEL_ID if CHANNEL_ID.startswith("-100") or CHANNEL_ID.startswith("@") else f"@{CHANNEL_ID}"

    print(f"Updating SEO for {chat_id} (Attempting to set new Name and Bio)...")

    try:
        # Update Name (Title)
        await bot.set_chat_title(chat_id=chat_id, title=NEW_NAME)
        print("[OK] Name updated successfully.")

        # Update Bio (Description)
        await bot.set_chat_description(chat_id=chat_id, description=NEW_BIO)
        print("[OK] Bio updated successfully.")
        
        print("\n[SUCCESS] SEO Optimization Complete! Your channel will now rank higher in Telegram Global Search.")

    except Exception as e:
        print(f"[ERROR] Failed to update SEO: {str(e).encode('ascii', 'ignore').decode('ascii')}")
        print("\nNote: Make sure the bot is an 'ADMIN' in the channel with 'Change Channel Info' permission.")

if __name__ == "__main__":
    asyncio.run(update_seo())
