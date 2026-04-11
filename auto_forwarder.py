import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Message
from dotenv import load_dotenv
import os
import time

# To use this, you need API_ID and API_HASH from https://my.telegram.org
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
CHANNEL_ID = os.getenv("CHANNEL_ID") # e.g. @your_channel (Your Deals Channel)

# List of Public Loot / Deals Groups (High Engagement)
TARGET_GROUPS = [
    "@Promoteclub_b",
    "@LootDealsIndia_Official",
    "@Offers_Deals_Loot_India",
    "@Amazon_Flipkart_Loot_Deals",
    "@ShoppingLootDeals",
    "@Loot_Deals_India_Official",
    "@OffersDealsLoot",
    "@AmazonFlipkartLoot",
    "@LootShoppingAtoZ",
    "@LootAlertsIndia",
    "@SastaBazar_Loot",
    "@Deals_Loot_India",
    "@Loot_offers_india",
    "@CouponLootDeals",
    "@IndiaFreeStuff_Loot",
    "@LootLoDeals",
    "@DailyLootDealsIndia",
    "@LootPriceAlerts",
    "@BestLootDeals",
    "@LootMastersIndia",
    "@LootKingIndia",
    "@LootVandals",
    "@LootExperts",
    "@LootMachao",
    "@LootEmpire",
    "@LootGurus"
]

# Family Network / Close Friends (Phone numbers or Usernames)
# Forwarding here looks like a personal message.
PRIORITY_CONTACTS = [
    # "919876543210", # Add family phone numbers here
    # "@friend_username"
]

STATE_FILE = "last_forwarded_id.txt"

def get_last_id():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def save_last_id(msg_id):
    with open(STATE_FILE, "w") as f:
        f.write(str(msg_id))

async def run_sync(client):
    print(f"\n[{time.strftime('%H:%M:%S')}] Starting sync cycle...")
    try:
        # Fetch the latest message from your channel
        print(f"Checking for new deals in {CHANNEL_ID}...")
        messages = await client.get_messages(CHANNEL_ID, limit=1)
        
        if not messages:
            print("[!] No messages found in channel.")
        else:
            latest_msg = messages[0]
            last_id = get_last_id()
            
            if latest_msg.id == last_id:
                print("[~] No new deals since last run. Exiting.")
            else:
                print(f"[+] Found new deal (ID: {latest_msg.id}). Forwarding...")
                
                # Forward to Public Groups
                for group in TARGET_GROUPS:
                    try:
                        # Try joining if not already in
                        try:
                            await client(JoinChannelRequest(group))
                        except: pass
                        
                        await client.forward_messages(group, latest_msg)
                        print(f"[OK] Sent to group: {group}")
                        await asyncio.sleep(10) # Safety delay
                    except Exception as e:
                        print(f"[!] Failed to send to {group}: {e}")

                # Forward to Family/Priority Contacts
                for contact in PRIORITY_CONTACTS:
                    try:
                        await client.forward_messages(contact, latest_msg)
                        print(f"[FAMILY] Sent to family: {contact}")
                        await asyncio.sleep(5)
                    except Exception as e:
                        print(f"[!] Failed to send to family {contact}: {e}")

                save_last_id(latest_msg.id)
                print(f"[OK] Sync complete. Last ID updated to {latest_msg.id}")
        
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")

async def main():
    if not API_ID or not API_HASH:
        print("[ERROR] API_ID and API_HASH not found in .env!")
        return

    print("Connecting to Telegram...")
    # Using Obfuscated connection to bypass ISP blocks in India (without needing a proxy)
    from telethon.network import ConnectionTcpObfuscated
    
    client = TelegramClient(
        'userbot_session', 
        int(API_ID), 
        API_HASH,
        connection=ConnectionTcpObfuscated,
        connection_retries=15,
        retry_delay=10
    )
    
    try:
        await client.start(phone=PHONE_NUMBER)
        print("[OK] Login Successful!")
        
        # Run a single sync cycle and then exit
        await run_sync(client)
        
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
