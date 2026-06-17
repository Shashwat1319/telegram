import asyncio
import os
import random
import json
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
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

MAX_CONCURRENT = 2  # Max parallel sends per account
DELAY_BETWEEN_BATCHES = 30  # seconds
DELAY_ON_ERROR = 60
WEEKLY_COOLDOWN_DAYS = 7

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

async def send_promo_semaphore(semaphore, session_env, contact, history, results):
    async with semaphore:
        client = get_client(session_env)
        if not client:
            results.append((contact, False, "No session"))
            return
        
        try:
            await asyncio.wait_for(client.connect(), timeout=30)
            
            if not await client.is_user_authorized():
                results.append((contact, False, "Not authorized"))
                return
            
            print(f"[*] Sending to {contact} via {session_env}...")
            await client.send_message(contact, PROMO_MESSAGE, link_preview=False)
            
            history[contact] = {
                "time": datetime.now().isoformat(),
                "account": session_env
            }
            results.append((contact, True, "Sent"))
            print(f"[OK] Sent to {contact}")
            
        except Exception as e:
            err = str(e).lower()
            if "flood" in err or "wait" in err:
                wait = random.randint(60, 120)
                print(f"[FLOOD] Waiting {wait}s...")
                await asyncio.sleep(wait)
            results.append((contact, False, str(e)[:100]))
            print(f"[ERROR] {contact}: {e}")
        finally:
            try:
                await client.disconnect()
            except: pass

async def process_batch(contacts_batch, session_env, history, semaphore):
    tasks = []
    for contact in contacts_batch:
        task = asyncio.create_task(send_promo_semaphore(semaphore, session_env, contact, history, []))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

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
            last_sent_dt = datetime.fromisoformat(ts)
            if now - last_sent_dt < timedelta(days=WEEKLY_COOLDOWN_DAYS):
                continue
        eligible.append(contact)
    
    print(f"[*] Eligible after cooldown: {len(eligible)} / {len(all_contacts)}")
    
    if not eligible:
        print("[!] All leads in cooldown.")
        return
    
    # Process with multiple accounts in parallel
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    for i in range(0, len(eligible), MAX_CONCURRENT * len(ACCOUNTS)):
        batch = eligible[i:i + MAX_CONCURRENT * len(ACCOUNTS)]
        print(f"\n[*] Processing batch {i//(MAX_CONCURRENT*len(ACCOUNTS)) + 1}: {len(batch)} contacts")
        
        # Distribute across accounts
        account_batches = [[] for _ in ACCOUNTS]
        for idx, contact in enumerate(batch):
            account_batches[idx % len(ACCOUNTS)].append(contact)
        
        # Run all accounts in parallel
        tasks = []
        for acc_idx, acc_batch in enumerate(account_batches):
            if acc_batch:
                task = asyncio.create_task(
                    process_batch(acc_batch, ACCOUNTS[acc_idx]["env"], history, semaphore)
                )
                tasks.append(task)
        
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and update history
        sent_count = 0
        for result_list in all_results:
            if isinstance(result_list, list):
                for contact, success, msg in result_list:
                    if success:
                        sent_count += 1
        
        save_history(history)
        print(f"[*] Batch done. Sent: {sent_count}")
        
        if i + MAX_CONCURRENT * len(ACCOUNTS) < len(eligible):
            print(f"[*] Waiting {DELAY_BETWEEN_BATCHES}s before next batch...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)
    
    print(f"\n[DONE] Total sent this run: Check history file")

if __name__ == "__main__":
    asyncio.run(main())