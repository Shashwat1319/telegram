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
GROUP_USERNAME = "FlipkartBitcoin"

async def main():
    print(f"[*] Starting Visibility Test for @{GROUP_USERNAME}...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    try:
        entity = await client.get_entity(GROUP_USERNAME)
        
        # 1. Send a test message
        print("[*] Sending test message...")
        msg = await client.send_message(entity, "🔍 Testing Group Visibility - Please Ignore")
        print(f"[*] Message sent (ID: {msg.id}). Waiting 15 seconds for bot reaction...")
        
        # 2. Wait to see if it gets deleted
        await asyncio.sleep(15)
        
        # 3. Check if it still exists
        try:
            messages = await client.get_messages(entity, ids=msg.id)
            if messages:
                print("[SUCCESS] Message is still visible! You ARE allowed to post here.")
            else:
                print("[FAILED] Message was INSTANTLY DELETED. This group has an anti-link/anti-spam bot.")
        except Exception as e:
            print(f"[FAILED] Error while checking message: {e}")
            
    except Exception as e:
        print(f"[!] Error during test: {e}")
        print("[HINT] If you get 'PeerIdInvalid', try joining the group manually first.")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
