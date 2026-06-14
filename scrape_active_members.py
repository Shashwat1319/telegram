import asyncio
import os
import json
from datetime import datetime, timedelta
from telethon import TelegramClient, functions, types
from telethon.tl.types import UserStatusRecently, UserStatusOnline
from dotenv import load_dotenv

# Load credentials
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE_NUMBER")

# Target groups to scrape from (Discussion groups of big deal channels)
TARGET_GROUPS = [
    "@cashbackoffersdiscussion",
    "@deals_groups",
    "@lootandtricks3",
    "@GhLoot_Offers_Discussion",
    "@offerswallchat",
    "@allrechargebill",
    "@LootDealsIndia_Chat",
    "@ShoppingDealsIndiaGroup",
    "@FreekaamaalDiscussion",
    "@DealOfTheDay_Chat"
]

LEADS_FILE = "scraped_leads.txt"
HISTORY_FILE = "promo_history.json"

async def get_active_members(client, group_username):
    print(f"[*] Scraping active members from {group_username}...")
    try:
        # Resolve entity first to make sure it's a channel/group
        try:
            entity = await client.get_entity(group_username)
            await client(functions.channels.JoinChannelRequest(channel=entity))
        except Exception as e:
            print(f"[-] Could not join/resolve {group_username}: {e}")
            # Skip this group if we cannot join
            return []

        active_users = []
        # Get recent messages to find people who are ACTUALLY chatting (High Intent)
        try:
            async for message in client.iter_messages(group_username, limit=300):
                if message.sender_id and not message.out:
                    sender = await message.get_sender()
                    if sender and not sender.bot and not sender.deleted:
                        if sender.username:
                            active_users.append(f"@{sender.username}")
                        elif sender.phone:
    for attempt in range(3):
        try:
            # Resolve entity first to make sure it's a channel/group
            try:
                entity = await client.get_entity(group_username)
                await client(functions.channels.JoinChannelRequest(channel=entity))
            except Exception as e:
                print(f"[-] Could not join/resolve {group_username}: {e}")
                return []

            active_users = []
            # Get recent messages to find people who are ACTUALLY chatting (High Intent)
            try:
                async for message in client.iter_messages(group_username, limit=300):
                    if message.sender_id and not message.out:
                        sender = await message.get_sender()
                        if sender and not sender.bot and not sender.deleted:
                            if sender.username:
                                active_users.append(f"@{sender.username}")
                            elif sender.phone:
                                active_users.append(f"+{sender.phone}")
            except Exception as e:
                print(f"[ERROR] Attempt {attempt+1}: Failed while iterating messages in {group_username}: {e}")
                await asyncio.sleep(2)
                continue
            
            # Remove duplicates
            active_users = list(set(active_users))
            
            print(f"[OK] Found {len(active_users)} highly active chatters in {group_username}")
            return active_users
        except Exception as e:
            print(f"[ERROR] Attempt {attempt+1}: Failed to scrape {group_username}: {e}")
            await asyncio.sleep(5)
    return []

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

async def main():
    if not API_ID or not API_HASH:
        print("[ERROR] API_ID/API_HASH missing in .env")
        return

    from telethon.sessions import StringSession
    session_data = os.getenv("TELEGRAM_SESSION_1")
    if session_data:
        client = TelegramClient(StringSession(session_data), int(API_ID), API_HASH)
    else:
        client = TelegramClient("userbot_session", int(API_ID), API_HASH)
    
    # [FIX] Use connect() not start() — start() prompts for OTP and hangs in automation
    await client.connect()
    if not await client.is_user_authorized():
        print("[ERROR] Session not authorized. Run generate_string_sessions.py to refresh.")
        await client.disconnect()
        return
    
    history = load_history()
    all_new_leads = set()
    
    # Load existing leads if file exists to avoid duplicates
    existing_leads = set()
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            existing_leads = {line.strip() for line in f if line.strip()}

    for group in TARGET_GROUPS:
        leads = await get_active_members(client, group)
        for lead in leads:
            # Only add if we haven't messaged them in the last 7 days (or ever)
            if lead not in history and lead not in existing_leads:
                all_new_leads.add(lead)
        
        await asyncio.sleep(5) # Delay between groups

    if all_new_leads:
        with open(LEADS_FILE, "a") as f:
            for lead in all_new_leads:
                f.write(f"{lead}\n")
        print(f"\n[SUCCESS] Added {len(all_new_leads)} NEW active leads to {LEADS_FILE}")
    else:
        print("\n[!] No new active leads found this time.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
