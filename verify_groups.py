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
GROUPS_FILE = "promo_groups_list.txt"

async def main():
    print(f"[*] Starting Bulk Group Verification...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    if not os.path.exists(GROUPS_FILE):
        print(f"[!] Error: {GROUPS_FILE} not found.")
        return

    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    verified_list = []
    failed_list = []

    for username in groups:
        clean_username = username.replace("@", "").strip()
        print(f"[*] Checking @{clean_username}...")
        
        try:
            entity = await client.get_entity(clean_username)
            
            # Check if it's a broadcast channel (usually read-only)
            if isinstance(entity, types.Channel) and getattr(entity, 'broadcast', False):
                print(f"    [X] Broadcast Channel (Read-Only). Skipping.")
                failed_list.append(f"{username} (Broadcast Channel)")
                continue

            # Check permissions
            try:
                # Try to join if not already a member
                try:
                    await client(functions.channels.JoinChannelRequest(entity))
                except: pass
                
                permissions = await client.get_permissions(entity)
                if permissions.send_messages:
                    print(f"    [OK] Active & Permitted.")
                    verified_list.append(username)
                else:
                    print(f"    [X] Restricted (Read-Only).")
                    failed_list.append(f"{username} (Restricted)")
            except Exception as e:
                print(f"    [X] Permission Error: {e}")
                failed_list.append(f"{username} (Error: {e})")
                
        except Exception as e:
            print(f"    [X] Could not find group: {e}")
            failed_list.append(f"{username} (Not Found)")
        
        await asyncio.sleep(1) # Safety delay

    # Write back the verified list
    with open("verified_promo_groups.txt", "w", encoding="utf-8") as f:
        f.write("# VERIFIED ACTIVE GROUPS\n")
        for g in verified_list:
            f.write(f"{g}\n")

    print(f"\n[DONE] Verification Summary:")
    print(f"    - Verified Active: {len(verified_list)}")
    print(f"    - Restricted/Failed: {len(failed_list)}")
    print(f"\n[*] Active groups saved to: verified_promo_groups.txt")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
