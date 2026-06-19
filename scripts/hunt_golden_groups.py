import asyncio
import os
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
    print(f"[*] Starting AGGRESSIVE Group Hunter...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    # 1. Broad Search Keywords
    keywords = [
        "loots discussion", "shopping chat india", "deals discussion", 
        "amazon loot chat", "flipkart deals chat", "sasta bazar discussion",
        "shopping groups india", "loot alert chat", "price drop discussion"
    ]
    
    found_verified = []
    
    for kw in keywords:
        print(f"\n[*] Searching for: '{kw}'")
        try:
            from telethon.tl.functions.contacts import SearchRequest
            result = await client(SearchRequest(q=kw, limit=50))
            
            for chat in result.chats:
                if len(found_verified) >= 20: break # Target 20 high-quality groups
                
                # We only want Groups/Megagroups (not channels)
                is_group = isinstance(chat, (types.Chat, types.Channel)) and not getattr(chat, 'broadcast', False)
                if not is_group or not chat.username:
                    continue
                
                username = chat.username
                print(f"    [?] Testing @{username}...")
                
                try:
                    # 1. Try to Join
                    await client(functions.channels.JoinChannelRequest(chat))
                    
                    # 2. Check Permissions for Sending Messages
                    permissions = await client.get_permissions(chat)
                    if permissions.send_messages:
                        # 3. VERIFICATION: Try to send a stealth message
                        test_msg = await client.send_message(chat, "Hello members! Are there any loot deals today?")
                        print(f"    [OK] Message Sent Successfully.")
                        
                        # 4. Final Confirmation: Wait and check if still exists
                        await asyncio.sleep(5)
                        messages = await client.get_messages(chat, ids=test_msg.id)
                        if messages:
                            print(f"    [GOLDEN] Verified! @{username} is OPEN.")
                            found_verified.append(f"@{username}")
                        else:
                            print(f"    [X] Message Deleted by Bot.")
                    else:
                        print(f"    [X] Restricted (Read-Only).")
                except Exception as e:
                    print(f"    [X] Failed: {e}")
                
                await asyncio.sleep(2) # Anti-Flood
                
        except Exception as e:
            print(f"[!] Error searching {kw}: {e}")
            
    # Save the GOLDEN list
    if found_verified:
        with open("verified_promo_groups.txt", "w", encoding="utf-8") as f:
            f.write("# 🔥 GOLDEN LIST - VERIFIED OPEN CHATS 🔥\n")
            for g in found_verified:
                f.write(f"{g}\n")
        print(f"\n[DONE] Found {len(found_verified)} GOLDEN groups. Saved to verified_promo_groups.txt")
    else:
        print("\n[FAILED] No open discussion groups found. Admins are too strict today!")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
