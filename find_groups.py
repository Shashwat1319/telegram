import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel
from dotenv import load_dotenv

async def find_20_groups():
    load_dotenv()
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE_NUMBER")

    client = TelegramClient("userbot_session", api_id, api_hash)
    await client.start(phone=phone)

    print("[*] Starting Telegram Global Search for Promo Groups...\n")
    
    keywords = ["sub4sub", "promote", "youtube subscribers", "share links", "telegram promote", "grow channel", "link sharing", "view4view"]
    found_groups = []
    
    for kw in keywords:
        if len(found_groups) >= 20:
            break
            
        print(f"[*] Searching for keyword: '{kw}'")
        try:
            result = await client(SearchRequest(
                q=kw,
                limit=30
            ))
            
            for chat in result.chats:
                if len(found_groups) >= 20:
                    break
                    
                if isinstance(chat, Channel) and not chat.broadcast:
                    # It's a supergroup
                    username = chat.username
                    if not username:
                        continue
                        
                    count = chat.participants_count if hasattr(chat, 'participants_count') else 0
                    if count is None or count == 0:
                        # Some versions don't return count directly in search, but we can assume popular search results have members.
                        # We will fetch full entity to get count
                        try:
                            entity = await client.get_entity(chat)
                            if hasattr(entity, 'participants_count'):
                                count = entity.participants_count
                        except: pass
                        
                    if count and count >= 100:
                        grp_name = f"@{username}"
                        if grp_name not in found_groups:
                            print(f"[OK] Found: {grp_name} ({count} members)")
                            found_groups.append(grp_name)
                            
        except Exception as e:
            print(f"[!] Search Error for '{kw}': {e}")
            
        await asyncio.sleep(2) # Prevent flood waits

    await client.disconnect()
    
    print(f"\n[*] Total valid groups found: {len(found_groups)}")
    if found_groups:
        with open("new_20_groups.txt", "w") as f:
            for g in found_groups:
                f.write(g + "\n")
        print("[*] Saved to new_20_groups.txt")

if __name__ == "__main__":
    asyncio.run(find_20_groups())
