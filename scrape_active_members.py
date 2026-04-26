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

        active_users = []
        # Get participants
        # We use limit=None to get as many as possible (Telethon handles pagination)
        # However, for safety and speed, we'll limit to 1000 per group for now
        async for user in client.iter_participants(group_username, limit=1000):
            if user.bot or user.deleted:
                continue
            
            # Check if user is "Recently" or "Online"
            is_active = isinstance(user.status, (UserStatusRecently, UserStatusOnline))
            
            if is_active:
                if user.username:
                    active_users.append(f"@{user.username}")
                elif user.phone:
                    active_users.append(f"+{user.phone}")
        
        print(f"[OK] Found {len(active_users)} active users in {group_username}")
        return active_users
    except Exception as e:
        print(f"[ERROR] Failed to scrape {group_username}: {e}")
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
    
    await client.start(phone=PHONE)
    
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
