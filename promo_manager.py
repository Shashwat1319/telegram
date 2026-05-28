import asyncio
import os
import random
import json
from telethon import TelegramClient, types, functions
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ACCOUNTS
ACCOUNTS = [
    {"phone": os.getenv("PHONE_NUMBER"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
    {"phone": os.getenv("PHONE_NUMBER_2"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
    {"phone": os.getenv("PHONE_NUMBER_3"), "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
]
SESSION_FILES = ["userbot_session", "worker_2_session", "worker_3_session"]

# Path to verified groups
GROUPS_FILE = "verified_promo_groups.txt"

def load_random_product():
    if os.path.exists("product.json"):
        with open("product.json", "r") as f:
            data = json.load(f)
            # Handle both list and dict formats
            products = data.get("products") if isinstance(data, dict) else data
            if products:
                return random.choice(products)
    return None

async def send_stealth_promo(group, session_name, acc):
    print(f"[*] Posting Stealth Promo to {group}...")
    product = load_random_product()
    if not product:
        print("[!] No product found for promo.")
        return False

    try:
        client = TelegramClient(session_name, acc["api_id"], acc["api_hash"])
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"[!] Session '{session_name}' not authorized.")
            await client.disconnect()
            return False

        # Prepare Message
        name = product.get('name', 'Deal of the Day')
        price = product.get('price', 'Check Price')
        # Use the Netlify tracker for the link
        raw_link = product.get('link', 'https://www.amazon.in/')
        short_link = f"https://budgetdeals-tracker-737523f4.netlify.app/.netlify/functions/go?url={raw_link}"
        
        caption = f"🔥 **UNBELIEVABLE LOOT DETECTED!** 🔥\n\n🛍️ **{name}**\n💰 Price: **{price}**\n\n🏃‍♂️ *Price can increase anytime! Click below to grab it before anyone else!* 👇\n\n"
        
        image_url = product.get('image')
        
        if image_url:
            await client.send_file(
                group, 
                image_url, 
                caption=caption,
                buttons=[types.KeyboardButtonUrl("🛒 BUY NOW (Amazon)", short_link)]
            )
        else:
            await client.send_message(group, caption + f"👉 Buy Now: {short_link}")

        print(f"[SUCCESS] Posted in {group}")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"[FAILED] Error in {group}: {e}")
        return False

async def main():
    print(f"[*] Starting Stealth Promo Cycle...")
    if not os.path.exists(GROUPS_FILE):
        print(f"[ERROR] No group list found.")
        return

    with open(GROUPS_FILE, "r") as f:
        groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not groups:
        print("[ERROR] No groups found.")
        return

    for i, group in enumerate(groups):
        session = SESSION_FILES[i % len(SESSION_FILES)]
        acc = ACCOUNTS[i % len(ACCOUNTS)]
        
        success = await send_stealth_promo(group, session, acc)
        if success:
            delay = random.randint(300, 600)
            print(f"[*] Waiting {delay}s...")
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
