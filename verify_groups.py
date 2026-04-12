import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from dotenv import load_dotenv

async def verify_groups():
    load_dotenv()
    try:
        api_id = int(os.getenv("API_ID"))
        api_hash = os.getenv("API_HASH")
        phone = os.getenv("PHONE_NUMBER")
    except:
        print("[ERROR] Missing API_ID or API_HASH in .env")
        return

    print("[*] Connecting to Telegram to verify groups...")
    client = TelegramClient("userbot_session", api_id, api_hash)
    
    try:
        await client.start(phone=phone)
    except Exception as e:
        print(f"[ERROR] Failed to start Telegram client: {e}")
        return

    try:
        with open("promo_groups_list.txt", "r") as f:
            groups = [line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")]
    except:
        print("[ERROR] promo_groups_list.txt not found.")
        return

    print(f"[*] Found {len(groups)} groups to verify. This might take a minute...\n")
    
    verified_list = []

    for group in groups:
        try:
            entity = await client.get_entity(group)
            
            # Skip if it's a user
            if hasattr(entity, 'first_name'):
                print(f"[-] {group}: Is a user, not a group.")
                continue

            # Need GetFullChannelRequest to get accurate participant count for megagroups
            full = await client(GetFullChannelRequest(channel=entity))
            count = full.full_chat.participants_count
            
            # Check if it's a broadcast channel (we usually can't post here unless admin)
            is_broadcast = getattr(entity, 'broadcast', False)
            
            if is_broadcast:
                print(f"[X] {group}: Is a broadcast channel (You can't post here without admin).")
            elif count and count >= 100:
                print(f"[OK] {group}: VALID ({count} members).")
                verified_list.append(group)
            else:
                print(f"[-] {group}: Too small ({count} members).")
                
        except ValueError:
            print(f"[X] {group}: Username not found or dead.")
        except Exception as e:
            print(f"[X] {group}: Error -> {e}")
            
        await asyncio.sleep(1) # Prevent FloodWait

    print("\n---------------------------------------------------------")
    print(f"[*] VERIFICATION COMPLETE. Found {len(verified_list)} working groups.")
    
    if verified_list:
        with open("verified_promo_groups.txt", "w") as f:
            for vg in verified_list:
                f.write(f"{vg}\n")
        print("[*] Saved working groups to 'verified_promo_groups.txt'")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_groups())
