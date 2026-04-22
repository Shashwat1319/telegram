import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Message
from telethon.network import ConnectionTcpObfuscated
from dotenv import load_dotenv
import os
import time
import random

# Load configuration
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
CHANNEL_ID = os.getenv("CHANNEL_ID") # e.g. @your_channel

# ✅ Discussion and Promo groups only (where members can chat/post)
TARGET_GROUPS_BASE = [
    "@Promoteclub_b",         # Verified Working
    "@Promote_Channel_Group",  # Promotion allowed
    "@Loot_Discussion_India", 
    "@Shopping_Loot_Discussion",
    "@Invite_Link_Group",
    "@Telegram_Promotion_India"
]

PRIORITY_GROUPS = ["@Promoteclub_b"]

# Multi-Account Setup (Main + Workers)
ACCOUNTS = [
    {"session": "userbot_session", "phone": os.getenv("PHONE_NUMBER")},
    {"session": "worker_2_session", "phone": os.getenv("PHONE_NUMBER_2")},
    {"session": "worker_3_session", "phone": os.getenv("PHONE_NUMBER_3")}
]

STATE_FILE = "last_forwarded_id.txt"
PROMO_COUNTER_FILE = "promo_counter.txt"

# Viral Recruitment Ad Message
PROMO_MESSAGE = f"""
✨ **GENUINE AMAZON PRICE DROPS DETECTED** ✨

Spam groups se pareshaan ho? Yahan sirf **Verified Budget Deals** post hoti hain, wo bhi Bina Hallucinations ke! 🛡️

✅ **Latest Deals posted just now:**
- 70% Off Branded Skincare
- Daily Use Gadgets under ₹499
- Verified Brand Sales

🔥 **JOIN FOR REAL SAVINGS:** https://t.me/{CHANNEL_ID.replace('@','')}
🔥 **JOIN FOR REAL SAVINGS:** https://t.me/{CHANNEL_ID.replace('@','')}

🚀 *We track prices 24/7 so you don't have to!*
"""

def get_last_id():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return int(f.read().strip())
        except: return 0
    return 0

def save_last_id(msg_id):
    with open(STATE_FILE, "w") as f:
        f.write(str(msg_id))

def check_should_promote():
    count = 0
    if os.path.exists(PROMO_COUNTER_FILE):
        try:
            with open(PROMO_COUNTER_FILE, "r") as f:
                count = int(f.read().strip())
        except: pass
    
    count += 1
    # Promote every 4 cycles (Balance between forwarding and growth)
    should_promo = (count >= 4)
    if should_promo:
        count = 0
    
    with open(PROMO_COUNTER_FILE, "w") as f:
        f.write(str(count))
    return should_promo

async def process_account(account_info, messages_to_forward, groups_to_target, run_promo=False):
    session_name = account_info["session"]
    phone = account_info["phone"]

    if not phone: return
    print(f"\n--- Account: {phone} ({session_name}) ---")
    
    # [NEW] Prefer String Session from Environment (for GitHub Actions)
    # Mapping: userbot_session -> TELEGRAM_SESSION_1, etc.
    session_map = {
        "userbot_session": "TELEGRAM_SESSION_1",
        "worker_2_session": "TELEGRAM_SESSION_2",
        "worker_3_session": "TELEGRAM_SESSION_3"
    }
    env_key = session_map.get(session_name)
    session_data = os.getenv(env_key) if env_key else None
    
    if session_data:
        print(f"[*] Using String Session from environment ({env_key}).")
        client = TelegramClient(
            StringSession(session_data),
            int(API_ID),
            API_HASH
        )
    else:
        print(f"[*] Using local session file ({session_name}).")
        client = TelegramClient(
            session_name, 
            int(API_ID), 
            API_HASH,
            connection=ConnectionTcpObfuscated if hasattr(ConnectionTcpObfuscated, '__name__') else None,
            connection_retries=15,
            retry_delay=10
        )
    
    try:
        await client.connect()
        # ... (rest of the code follows)
        if not await client.is_user_authorized():
            print(f"[!] Session {session_name} is NOT authorized. Skipping to avoid background OTP hang.")
            await client.disconnect()
            return

        print(f"[OK] Connected.")
        
        # 1. Forward regular messages (fallback to promo if can't forward)
        for msg in messages_to_forward:
            for group in groups_to_target:
                # [SHIELD] Prevent forwarding back to the source channel
                if group.lower() == CHANNEL_ID.lower():
                    # print(f"[*] Skipping {group}: Destination is same as source.")
                    continue

                try:
                    try: await client(JoinChannelRequest(group))
                    except: pass
                    await client.forward_messages(group, msg)
                    print(f"[OK] Forwarded ID {msg.id} -> {group}")
                    await asyncio.sleep(random.randint(5, 10))
                except Exception as e:
                    err = str(e).lower()
                    if "admin privileges" in err or "channel" in err:
                        # Clearer message for Read-only channels
                        print(f"[-] Skipping {group}: Read-only Channel (No permission)")
                        # Fallback to promo invite (sometimes works in linked discussion)
                        try:
                            await client.send_message(group, PROMO_MESSAGE, link_preview=False)
                            print(f"[PROMO] Invite sent to {group}")
                            await asyncio.sleep(random.randint(15, 25))
                        except: pass
                    elif "username" in err or "resolve" in err:
                        print(f"[!] Group {group} skipped: Invalid Username")
                    else:
                        print(f"[!] Group {group} skipped: {e}")

        # 2. RUN GROWTH MISSION (If cycle hit)
        if run_promo:
            print(f"[*] MISSION 200: Sending Viral Ad to groups...")
            for group in groups_to_target:
                try:
                    await client.send_message(group, PROMO_MESSAGE, link_preview=False)
                    print(f"[GROWTH] Promo sent to {group}")
                    await asyncio.sleep(random.randint(20, 40))
                except Exception as e:
                    if "admin privileges" in str(e):
                        print(f"[-] {group} promo skipped: No permission")
                    else:
                        print(f"[!] Promo failed for {group}: {e}")
            
    except Exception as e:
        print(f"[ERROR] Session {session_name} failed: {e}")
    finally:
        await client.disconnect()

async def main():
    if not API_ID or not API_HASH:
        print("[ERROR] API_ID or API_HASH missing in .env")
        return

    should_promo_now = check_should_promote()
    
    print("Fetching new deals...")
    fetcher_client = TelegramClient(ACCOUNTS[0]["session"], int(API_ID), API_HASH)
    
    new_messages = []
    try:
        await fetcher_client.start(phone=ACCOUNTS[0]["phone"])
        last_id = get_last_id()
        async for message in fetcher_client.iter_messages(CHANNEL_ID, min_id=last_id, limit=20):
            if message.text or message.media:
                new_messages.append(message)
        await fetcher_client.disconnect()
    except Exception as e:
        print(f"[!] Fetching failed: {e}")
        return

    if not new_messages and not should_promo_now:
        print(f"[{time.strftime('%H:%M:%S')}] Nothing to do this cycle.")
        return

    new_messages.reverse()
    active_accounts = [acc for acc in ACCOUNTS if acc.get("phone")]
    
    tasks = []
    n = len(active_accounts)
    chunk_size = len(TARGET_GROUPS_BASE) // n
    
    for i, acc in enumerate(active_accounts):
        start = i * chunk_size
        end = len(TARGET_GROUPS_BASE) if i == n - 1 else (i + 1) * chunk_size
        splits = TARGET_GROUPS_BASE[start:end] + PRIORITY_GROUPS
        tasks.append(process_account(acc, new_messages, splits, run_promo=should_promo_now))

    if tasks:
        print(f"[*] Starting Cycle (Promo Mode: {should_promo_now})...")
        await asyncio.gather(*tasks)

    if new_messages:
        save_last_id(new_messages[-1].id)

    print(f"\n[{time.strftime('%H:%M:%S')}] Sync cycle finished.")

if __name__ == "__main__":
    asyncio.run(main())
