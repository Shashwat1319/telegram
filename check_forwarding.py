import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

async def check_forwarding():
    load_dotenv()
    try:
        api_id = int(os.getenv("API_ID"))
        api_hash = os.getenv("API_HASH")
        phone = os.getenv("PHONE_NUMBER")
    except:
        print("[ERROR] Missing API_ID or API_HASH in .env")
        return

    print("[*] Connecting to check group permissions...")
    client = TelegramClient("userbot_session", api_id, api_hash)
    
    try:
        await client.start(phone=phone)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    try:
        with open("new_20_groups.txt", "r") as f:
            groups = [line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")]
    except:
        print("[ERROR] File new_20_groups.txt not found.")
        return

    forwardable_groups = []

    for group in groups:
        try:
            entity = await client.get_entity(group)
            
            banned = getattr(entity, 'default_banned_rights', None)
            can_send = True
            
            if banned:
                if banned.send_messages:
                    can_send = False
            
            is_broadcast = getattr(entity, 'broadcast', False)
            if is_broadcast:
                can_send = False

            if can_send:
                print(f"[YES] {group}: Open to normal members.")
                forwardable_groups.append(group)
            else:
                print(f"[NO] {group}: Restricted or Read-Only.")
                
        except ValueError:
            pass # Ignore invalid ones silently
        except Exception as e:
            print(f"[!] {group} error: {e}")
            
        await asyncio.sleep(1) # Prevent FloodWait

    print("\n---------------------------------------------------------")
    print(f"[*] Found {len(forwardable_groups)} groups that allow you to post/forward.")
    
    if forwardable_groups:
        with open("verified_promo_groups.txt", "w") as f:
            for vg in forwardable_groups:
                f.write(f"{vg}\n")
        print("[*] Overwritten 'verified_promo_groups.txt' with the cleanest list.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(check_forwarding())
