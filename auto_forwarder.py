import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest
from dotenv import load_dotenv
import os
import time

# To use this, you need API_ID and API_HASH from https://my.telegram.org
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
CHANNEL_ID = os.getenv("CHANNEL_ID") # e.g. @your_channel (Your Deals Channel)

# List of Public Promo / Free Posting Groups.
# IMPORTANT: Aap Telegram par 'Sub4Sub', 'Promotion', 'Loot Discussion' 
# search karke jo groups mile unhe yaha list me add kar dena.
TARGET_GROUPS = [
    "@YouTube_Sub4Sub_Subscriber",
    "@Free_Promotion_Group",
    "@link_promoting_group",
    "@sub4sub_indian_youtubers",
    "@deals_and_loot_discussion",
    "@amazon_flipkart_discussion"
]

async def main():
    if not API_ID or not API_HASH:
        print("❌ Error: API_ID aur API_HASH .env file me set karo (get it from https://my.telegram.org)!")
        return

    print("Logging in to your Telegram account (Userbot mode)...")
    client = TelegramClient('userbot_session', int(API_ID), API_HASH)
    await client.start(phone=PHONE_NUMBER)
    print("✅ Login Successful!")

    # Fetch the latest message from your channel
    print(f"Fetching latest deal from {CHANNEL_ID}...")
    messages = await client.get_messages(CHANNEL_ID, limit=1)
    
    if not messages:
        print("❌ Channel par koi message nahi mila!")
        return
        
    latest_msg = messages[0]
    
    print(f"Forwarding message to {len(TARGET_GROUPS)} groups...")
    for group in TARGET_GROUPS:
        try:
            # Phele public group join karenge
            try:
                await client(JoinChannelRequest(group))
            except Exception:
                pass # Already joined hoga ya error
                
            # Channel se message utha kar as a human forward karenge
            await client.forward_messages(group, latest_msg)
            print(f"✅ Successfully sent to {group}")
            
            # Anti-ban strict delay (Bohot zaroori hai ban se bachne ke liye)
            print("Chilling for 15 seconds to avoid spam ban...")
            time.sleep(15)
        except Exception as e:
            print(f"❌ Failed to send to {group}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
