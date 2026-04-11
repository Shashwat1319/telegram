import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Message
from telethon.network import ConnectionTcpObfuscated
from dotenv import load_dotenv
import os
import time

# Load configuration
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
CHANNEL_ID = os.getenv("CHANNEL_ID") # e.g. @your_channel

# Target Communities
TARGET_GROUPS_BASE = [
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

# Priority Groups for ALL accounts
PRIORITY_GROUPS = ["@Promoteclub_b"]

# Multi-Account Setup
ACCOUNTS = [
    {"session": "userbot_session", "phone": os.getenv("PHONE_NUMBER")},
    {"session": "worker_2_session", "phone": os.getenv("PHONE_NUMBER_2")}
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

async def run_sync_for_account(account_info, groups_to_target):
    session_name = account_info["session"]
    phone = account_info["phone"]

    if not phone:
        print(f"[SKIP] No phone number for {session_name}")
        return

    print(f"\n--- Starting Sync for: {phone} ({session_name}) ---")
    
    client = TelegramClient(
        session_name, 
        int(API_ID), 
        API_HASH,
        connection=ConnectionTcpObfuscated,
        connection_retries=15,
        retry_delay=10
    )
    
    try:
        await client.start(phone=phone)
        print(f"[OK] Connected as {phone}")
        
        last_id = get_last_id()
        print(f"Scanning {CHANNEL_ID} for deals after ID {last_id}...")
        
        new_messages = []
        async for message in client.iter_messages(CHANNEL_ID, min_id=last_id, limit=20):
            if message.text or message.media:
                new_messages.append(message)
        
        if not new_messages:
            print(f"[~] No new deals found for this account.")
            return

        new_messages.reverse()
        
        for msg in new_messages:
            for group in groups_to_target:
                try:
                    # Auto-join if needed
                    try:
                        await client(JoinChannelRequest(group))
                    except: pass
                    
                    await client.forward_messages(group, msg)
                    print(f"[OK] Forwarded ID {msg.id} -> {group}")
                    await asyncio.sleep(8) # Anti-Spam delay
                except Exception as e:
                    print(f"[!] Error for group {group}: {e}")
            
            save_last_id(msg.id)
            
    except Exception as e:
        print(f"[ERROR] Session {session_name} failed: {e}")
    finally:
        await client.disconnect()

async def main():
    if not API_ID or not API_HASH:
        print("[ERROR] API_ID or API_HASH missing in .env")
        return

    # Account Logic
    active_accounts = [acc for acc in ACCOUNTS if acc["phone"]]
    
    if len(active_accounts) == 1:
        # Single account mode
        await run_sync_for_account(active_accounts[0], TARGET_GROUPS_BASE + PRIORITY_GROUPS)
    elif len(active_accounts) > 1:
        # Multi-account split mode
        mid = len(TARGET_GROUPS_BASE) // 2
        splits = [
            TARGET_GROUPS_BASE[:mid] + PRIORITY_GROUPS,
            TARGET_GROUPS_BASE[mid:] + PRIORITY_GROUPS
        ]
        for i, acc in enumerate(active_accounts):
            await run_sync_for_account(acc, splits[i])

    print(f"\n[{time.strftime('%H:%M:%S')}] Entire sync cycle finished.")

if __name__ == "__main__":
    asyncio.run(main())
