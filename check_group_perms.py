import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

def load_groups():
    groups = []
    if os.path.exists("verified_promo_groups.txt"):
        with open("verified_promo_groups.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    groups.append(line)
    return groups

async def check_perms():
    groups = load_groups()
    session_data = os.getenv("TELEGRAM_SESSION_1")
    client = TelegramClient(StringSession(session_data), int(API_ID), API_HASH)
    
    await client.connect()
    print(f"--- Group Permission Audit ---")
    
    results = []
    for group in groups:
        try:
            entity = await client.get_entity(group)
            # Try to see if we can send a "test" (but don't actually send if possible)
            # Or just check participant rights
            full = await client(functions.channels.GetFullChannelRequest(channel=entity))
            can_send = not full.full_chat.can_view_participants # This is not reliable
            
            # Real test: try to send a message and immediately delete it (if allowed)
            # But let's just check the 'broadcast' flag and 'restricted' flag
            if hasattr(entity, 'broadcast') and entity.broadcast:
                status = "Channel (Read-Only)"
            else:
                status = "Group/Supergroup (Check Manual)"
            
            print(f"[*] {group}: {status}")
            results.append((group, status))
        except Exception as e:
            print(f"[!] {group}: Error ({e})")
            results.append((group, f"Error: {e}"))
            
    await client.disconnect()

if __name__ == "__main__":
    from telethon import functions
    asyncio.run(check_perms())
