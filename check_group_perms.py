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
    print(f"[*] Inspecting Group: @{GROUP_USERNAME}...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    try:
        entity = await client.get_entity(GROUP_USERNAME)
        print(f"[*] Title: {entity.title}")
        
        full_chat = await client(functions.channels.GetFullChannelRequest(channel=entity))
        about = full_chat.full_chat.about if full_chat.full_chat.about else "No description"
        print(f"[*] About: {about}")
        
        # Check permissions
        try:
            permissions = await client.get_permissions(entity)
            print(f"[*] Permissions Found:")
            print(f"    - Can send messages: {permissions.send_messages}")
            print(f"    - Can send media: {permissions.send_media}")
            print(f"    - Is Admin: {permissions.is_admin}")
        except:
            print("[!] Could not fetch specific permissions (might not be in the group).")
            
    except Exception as e:
        print(f"[!] Error during inspection: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
