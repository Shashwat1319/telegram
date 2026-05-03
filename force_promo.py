import asyncio
import os
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHANNEL_ID = os.getenv("CHANNEL_ID")

PROMO_MESSAGE = f"""
🚨 **AMAZON LOOT: ₹99 Store Unlocked!** 🚨

Bhai jaldi join kar, Amazon par price glitch hua hai. Sab kuch ₹99-₹199 mein mil raha hai! 😱🔥

👇 **JALDI JOIN KARO (Link Expiring):**
https://t.me/{CHANNEL_ID.replace('@','')}
https://t.me/{CHANNEL_ID.replace('@','')}

*Abhi join karo, loot miss mat karna!* 🏃‍♂️💨
"""

GROUPS = [
    "@cashbackoffersdiscussion", "@deals_groups", "@lootandtricks3",
    "@GhLoot_Offers_Discussion", "@offerswallchat", "@allrechargebill",
    "@onlinelootrjgroup", "@LootDealsDiscussion", "@lootspotindia",
    "@lootdailyoffers", "@vaasutechvlogs", "@TechFactsDisQus",
    "@offersanddealsdiscussion", "@DealsDiscussion", "@LootChat"
]

async def force_promo():
    session_data = os.getenv("TELEGRAM_SESSION_1")
    client = TelegramClient(StringSession(session_data), int(API_ID), API_HASH)
    await client.connect()
    
    print(f"[*] Starting FORCE PROMO to {len(GROUPS)} groups...")
    for group in GROUPS:
        try:
            await client.send_message(group, PROMO_MESSAGE, link_preview=False)
            print(f"[OK] Sent to {group}")
            await asyncio.sleep(random.randint(30, 60))
        except Exception as e:
            print(f"[ERROR] Failed for {group}: {e}")
            
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(force_promo())
