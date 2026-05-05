import os
import asyncio
import sys
from telethon import TelegramClient, functions, types
from dotenv import load_dotenv

# Set encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = "userbot_session"
GROUP_USERNAME = "deals_groups"

async def main():
    print(f"[*] Deep Analysis for @{GROUP_USERNAME}...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    try:
        entity = await client.get_entity(GROUP_USERNAME)
        
        # 1. Check if we are in the group
        try:
            participant = await client(functions.channels.GetParticipantRequest(
                channel=entity,
                participant=await client.get_me()
            ))
            print(f"[*] You are a member of the group. Role: {type(participant.participant).__name__}")
        except Exception as e:
            print(f"[!] You are NOT a member of this group or could not fetch status: {e}")
            print("[*] Attempting to join...")
            try:
                await client(functions.channels.JoinChannelRequest(entity))
                print("[SUCCESS] Joined the group.")
            except Exception as join_e:
                print(f"[FAILED] Could not join: {join_e}")
        
        # 2. Check Global Chat Restrictions
        full_chat = await client(functions.channels.GetFullChannelRequest(channel=entity))
        if hasattr(full_chat.full_chat, 'default_banned_rights'):
            rights = full_chat.full_chat.default_banned_rights
            if rights:
                print(f"[*] Group-wide Restrictions:")
                print(f"    - Send Messages restricted: {rights.send_messages}")
                print(f"    - Send Media restricted: {rights.send_media}")
        
    except Exception as e:
        print(f"[!] Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
