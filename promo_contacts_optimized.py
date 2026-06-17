import asyncio
import os
import random
import json
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHANNEL_ID = os.getenv("CHANNEL_ID")

PROMO_MESSAGE = f"""
🔥 **Student Loot Alert: Branded Items at \u20b999!** 🔥

Bhai, Amazon par massive price drop hua hai selected electronics aur daily gadgets par. Branded Earphones aur Home utilities abhi \u20b999 - \u20b9199 mein mil rahe hain. 😱

Maine saare **Verified 4-Star+** deals channel par daal di hain. Jaldi check kar lo warna stock out ho jayega!

👇 **LOOT ACCESS (Verified Links):**
https://t.me/{CHANNEL_ID.replace('@','')}
https://t.me/{CHANNEL_ID.replace('@','')}

✅ *No Scam, Only Real Hand-picked Deals!*
"""

ACCOUNTS = [
    {"session": "userbot_session", "env": "TELEGRAM_SESSION_1"},
    {"session": "worker_2_session", "env": "TELEGRAM_SESSION_2"},
    {"session": "worker_3_session", "env": "TELEGRAM_SESSION_3"}
]

HISTORY_FILE = "promo_history.json"
LEADS_FILE = "scraped_leads.txt"

MAX_CONCURRENT_PER_ACCOUNT = 1  # 1 at a time per account (Telegram limit)
DELAY_BETWEEN_SENDS = 30  # seconds between sends per account
DELAY_ON_FLOOD = 60
WEEKLY_COOLDOWN_DAYS = 7
MAX_RETRIES = 3

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def get_client(session_env):
    session_data = os.getenv(session_env)
    if session_data:
        return TelegramClient(StringSession(session_data), int(API_ID), API_HASH)
    return None

async def send_with_retry(client, contact, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            await client.send_message(contact, PROMO_MESSAGE, link_preview=False)
            return True, "Sent"
        except FloodWaitError as e:
            wait_time = e.seconds + random.randint(5, 15)
            print(f"[FLOOD] Account waiting {wait_time}s (attempt {attempt+1}/{retries})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            err = str(e).lower()
            if "flood" in err or "wait" in err:
                wait_time = random.randint(60, 120)
                print(f"[FLOOD] Generic wait {wait_time}s")
                await asyncio.sleep(wait_time)
            elif "peer" in err or "user" in err or "chat" in err:
                return False, f"Invalid contact: {e}"
            else:
                print(f"[ERROR] {contact}: {e}")
                await asyncio.sleep(DELAY_ON_FLOOD)
    return False, f"Max retries exceeded"

async def process_account_queue(account_env, contacts, history, results_queue):
    """Process contacts for a single account sequentially."""
    client = get_client(account_env)
    if not client:
        for contact in contacts:
            await results_queue.put((contact, False, "No session"))
        return
    
    try:
        await asyncio.wait_for(client.connect(), timeout=30)
        
        if not await client.is_user_authorized():
            print(f"[SKIP] {account_env}: Not authorized")
            for contact in contacts:
                await results_queue.put((contact, False, "Not authorized"))
            return
        
        print(f"[*] {account_env}: Processing {len(contacts)} contacts")
        
        for contact in contacts:
            success, msg = await send_with_retry(client, contact)
            if success:
                history[contact] = {
                    "time": datetime.now().isoformat(),
                    "account": account_env
                }
            await results_queue.put((contact, success, msg))
            
            # Delay between sends to avoid rate limits
            await asyncio.sleep(DELAY_BETWEEN_SENDS + random.randint(0, 10))
            
    except Exception as e:
        print(f"[ACCOUNT ERROR] {account_env}: {e}")
        for contact in contacts:
            await results_queue.put((contact, False, str(e)[:100]))
    finally:
        try:
            await client.disconnect()
        except: pass

async def main():
    history = load_history()
    now = datetime.now()
    
    # Load leads
    all_contacts = []
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            scraped = [line.strip() for line in f if line.strip()]
            all_contacts.extend(scraped)
            print(f"[*] Loaded {len(scraped)} scraped leads.")
    
    for account in ACCOUNTS:
        filename = f"contacts_{account['session']}.txt"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                ac_contacts = [line.strip() for line in f if line.strip()]
                all_contacts.extend(ac_contacts)
    
    # Deduplicate
    seen = set()
    all_contacts = [x for x in all_contacts if not (x in seen or seen.add(x))]
    
    if not all_contacts:
        print("[!] No leads found.")
        return
    
    # Filter by cooldown
    eligible = []
    for contact in all_contacts:
        last_sent = history.get(contact)
        if last_sent:
            ts = last_sent["time"] if isinstance(last_sent, dict) else last_sent
            try:
                last_sent_dt = datetime.fromisoformat(ts)
                if now - last_sent_dt < timedelta(days=WEEKLY_COOLDOWN_DAYS):
                    continue
            except:
                pass
        eligible.append(contact)
    
    print(f"[*] Eligible after cooldown: {len(eligible)} / {len(all_contacts)}")
    
    if not eligible:
        print("[!] All leads in cooldown.")
        return
    
    # Distribute contacts across accounts
    account_queues = [[] for _ in ACCOUNTS]
    for idx, contact in enumerate(eligible):
        account_queues[idx % len(ACCOUNTS)].append(contact)
    
    # Process all accounts in parallel
    results_queue = asyncio.Queue()
    tasks = []
    
    for acc_idx, acc_contacts in enumerate(account_queues):
        if acc_contacts:
            task = asyncio.create_task(
                process_account_queue(ACCOUNTS[acc_idx]["env"], acc_contacts, history, results_queue)
            )
            tasks.append(task)
    
    # Wait for all accounts to finish
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    sent_count = 0
    failed_count = 0
    while not results_queue.empty():
        contact, success, msg = await results_queue.get()
        if success:
            sent_count += 1
        else:
            failed_count += 1
    
    save_history(history)
    print(f"\n[DONE] Sent: {sent_count}, Failed: {failed_count}, Total eligible: {len(eligible)}")

if __name__ == "__main__":
    asyncio.run(main())