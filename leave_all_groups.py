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

async def main():
    print(f"[*] Starting cleanup for {SESSION_NAME}...")
    
    # Check if session file exists
    if not os.path.exists(f"{SESSION_NAME}.session"):
        print(f"[!] Error: {SESSION_NAME}.session not found in current directory.")
        return

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    me = await client.get_me()
    print(f"[*] Logged in as: {me.first_name} (@{me.username if me.username else 'NoUsername'})")
    
    print("[*] Fetching groups... this might take a moment.")
    count = 0
    
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        
        # We want to leave Groups and Megagroups
        is_megagroup = isinstance(entity, types.Channel) and not getattr(entity, 'broadcast', False)
        is_chat = isinstance(entity, types.Chat)
        
        if is_megagroup or is_chat:
            try:
                # Check if it's not the user's own channel (safety check)
                if hasattr(entity, 'username') and entity.username and "budgetdeals_india" in entity.username.lower():
                    print(f"[SKIP] Skipping your own channel: {dialog.name}")
                    continue
                    
                print(f"[-] Leaving group: {dialog.name} (ID: {dialog.id})")
                
                if is_megagroup:
                    await client(functions.channels.LeaveChannelRequest(entity))
                else:
                    await client(functions.messages.DeleteChatUserRequest(chat_id=entity.id, user_id='me'))
                
                count += 1
                await asyncio.sleep(0.5) # Fast but safe
            except Exception as e:
                print(f"[!] Could not leave {dialog.name}: {e}")

    print(f"\n[DONE] Successfully left {count} groups.")
    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Operation cancelled by user.")
