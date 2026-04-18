import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel
from dotenv import load_dotenv

async def find_shopping_groups():
    load_dotenv()
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE_NUMBER")

    client = TelegramClient("userbot_session", api_id, api_hash)
    await client.start(phone=phone)

    print("[*] Searching for High-Quality Shopping Discussion Groups...\n")
    
    # Better keywords to find ACTUAL shoppers
    keywords = [
        "shopping discussion", "loot deals chat", "amazon deals india", 
        "flipkart loot discussion", "price glitch chat", "sasta shopping",
        "loot offers discussion", "coupons india chat"
    ]
    
    found_groups = []
    
    for kw in keywords:
        print(f"[*] Searching: '{kw}'")
        try:
            result = await client(SearchRequest(q=kw, limit=50))
            
            for chat in result.chats:
                if isinstance(chat, Channel) and not chat.broadcast:
                    username = chat.username
                    if not username: continue
                    
                    # Estimate member count
                    count = getattr(chat, 'participants_count', 0)
                    if count is None or count < 100:
                        try:
                            entity = await client.get_entity(chat)
                            count = getattr(entity, 'participants_count', 0)
                        except: pass
                    
                    if count and count >= 500: # Only big active groups
                        grp_name = f"@{username}"
                        if grp_name not in found_groups:
                            print(f"[OK] Found: {grp_name} ({count} members)")
                            found_groups.append(grp_name)
                            
        except Exception as e:
            print(f"[!] Error for '{kw}': {e}")
            
        await asyncio.sleep(2)

    await client.disconnect()
    
    if found_groups:
        with open("promo_groups_list.txt", "a") as f: # Append to existing list
            f.write("\n# --- EXPANDED GROUPS ---\n")
            for g in found_groups:
                f.write(g + "\n")
        print(f"\n[*] Added {len(found_groups)} new groups to promo_groups_list.txt")
    else:
        print("\n[!] No new groups found.")

if __name__ == "__main__":
    asyncio.run(find_shopping_groups())
