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
    "@LootLoDeals",
    "@LootMastersIndia"
]

# Priority Groups for ALL accounts
PRIORITY_GROUPS = ["@Promoteclub_b","@PromoteClub"]

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

async def process_account(account_info, messages_to_forward, groups_to_target):
    session_name = account_info["session"]
    phone = account_info["phone"]

    print(f"\n--- Account: {phone} ({session_name}) ---")
    
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
        print(f"[OK] Connected.")
        
        for msg in messages_to_forward:
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
                    print(f"[!] Group {group} error: {e}")
            
    except Exception as e:
        print(f"[ERROR] Session {session_name} failed: {e}")
    finally:
        await client.disconnect()

async def main():
    if not API_ID or not API_HASH:
        print("[ERROR] API_ID or API_HASH missing in .env")
        return

    # 1. First, find out what needs to be forwarded (using Account 1)
    print("Fetching new deals...")
    fetcher_client = TelegramClient(
        ACCOUNTS[0]["session"], 
        int(API_ID), 
        API_HASH,
        connection=ConnectionTcpObfuscated
    )
    
    new_messages = []
    try:
        await fetcher_client.start(phone=ACCOUNTS[0]["phone"])
        last_id = get_last_id()
        print(f"Checking for deals in {CHANNEL_ID} with ID > {last_id}...")
        
        async for message in fetcher_client.iter_messages(CHANNEL_ID, min_id=last_id, limit=20):
            print(f"Found message ID: {message.id}")
            if message.text or message.media:
                new_messages.append(message)
        await fetcher_client.disconnect()
    except Exception as e:
        print(f"[!] Fetching failed: {e}")
        return

    if not new_messages:
        print(f"[{time.strftime('%H:%M:%S')}] No new deals to forward.")
        return

    new_messages.reverse() # Oldest first
    print(f"[+] Found {len(new_messages)} new deals to forward to all accounts.")

    # 2. Split groups and process with all active accounts in parallel
    active_accounts = [acc for acc in ACCOUNTS if acc.get("phone")]
    
    tasks = []
    if len(active_accounts) == 1:
        tasks.append(process_account(active_accounts[0], new_messages, TARGET_GROUPS_BASE + PRIORITY_GROUPS))
    elif len(active_accounts) > 1:
        mid = len(TARGET_GROUPS_BASE) // 2
        splits = [
            TARGET_GROUPS_BASE[:mid] + PRIORITY_GROUPS,
            TARGET_GROUPS_BASE[mid:] + PRIORITY_GROUPS
        ]
        for i, acc in enumerate(active_accounts):
            tasks.append(process_account(acc, new_messages, splits[i]))

    if tasks:
        print(f"[*] Dispatching {len(tasks)} accounts for parallel forwarding...")
        await asyncio.gather(*tasks)

    # 3. Update the global state after ALL accounts finished their job
    if new_messages:
        save_last_id(new_messages[-1].id)
        print(f"\n[OK] State updated to ID {new_messages[-1].id}")

    print(f"\n[{time.strftime('%H:%M:%S')}] Sync cycle finished.")

if __name__ == "__main__":
    asyncio.run(main())
