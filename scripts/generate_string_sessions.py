import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load configuration
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

ACCOUNTS = [
    {"session": "userbot_session", "phone": os.getenv("PHONE_NUMBER"), "label": "MAIN ACCOUNT"},
    {"session": "worker_2_session", "phone": os.getenv("PHONE_NUMBER_2"), "label": "WORKER 2"},
    {"session": "worker_3_session", "phone": os.getenv("PHONE_NUMBER_3"), "label": "WORKER 3"}
]

async def generate_string(account):
    session_name = account["session"]
    phone = account["phone"]
    label = account["label"]
    
    if not phone:
        return None

    print(f"\n--- Generating String Session for: {label} ({phone}) ---")
    
    # 1. Connect to the EXISTING authorized session file
    client = TelegramClient(session_name, int(API_ID), API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"[!] Session {session_name} is NOT authorized. Please run fix_telegram_sessions.py first.")
            return None
        
        # 2. Export the session as a string
        session_string = StringSession.save(client.session)
        return session_string
    except Exception as e:
        print(f"[ERROR] Failed for {label}: {e}")
        return None
    finally:
        await client.disconnect()

async def main():
    print("--- Telethon String Session Generator ---")
    print("This will convert your local .session files into text strings for GitHub Secrets.")
    
    results = []
    for acc in ACCOUNTS:
        string = await generate_string(acc)
        if string:
            results.append((acc['label'], string))
    
    if results:
        print("\n" + "="*80)
        print("COPY THESE STRINGS TO GITHUB SECRETS (Settings > Secrets > Actions)")
        print("="*80)
        for i, (label, string) in enumerate(results, 1):
            print(f"\n[ SECRET NAME: TELEGRAM_SESSION_{i} ]")
            print(f"[ ACCOUNT: {label} ]")
            print("-" * 20)
            print(string)
            print("-" * 20)
        print("\n" + "="*80)
        print("IMPORTANT: Keep these strings SECRET. Anyone with these strings can access your Telegram.")
    else:
        print("\nNo strings generated. Ensure your local sessions are authorized.")

if __name__ == "__main__":
    asyncio.run(main())
