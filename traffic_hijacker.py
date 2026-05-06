import asyncio
import os
import random
import requests
import re
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ACCOUNTS FOR COMMENTING (Worker accounts to keep main channel safe)
WORKERS = [
    {"session": "worker_2_session", "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
    {"session": "worker_3_session", "api_id": os.getenv("API_ID"), "api_hash": os.getenv("API_HASH")},
]

# TARGET BIG CHANNELS (Where we will leave comments)
TARGET_CHANNELS = [
    "deals_bay", "FlipkartBitcoin", "dealsmania_loot", "LootDealsIndia7", "ShoppingLoots", "cashbackoffersdiscussion"
]

CHANNEL_LINK = f"https://t.me/{os.getenv('CHANNEL_ID', 'budgetdeals_india').replace('@', '')}"

def generate_ai_reply(original_text):
    """Use Gemini to generate a contextual, human-like reply."""
    if not GEMINI_API_KEY or not original_text:
        return random.choice([
            f"Bhai yahan aur sasta mil raha hai! Check kro: {CHANNEL_LINK}",
            f"Price drop alert! Yahan better deals hain 😱: {CHANNEL_LINK}"
        ])

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    You are a helpful, enthusiastic Indian shopper in a Telegram deal group.
    Someone just posted this deal: "{original_text[:200]}"

    Write a very short, casual reply (1-2 sentences max) in Hinglish.
    The goal is to casually mention that even better loots or a cheaper alternative is available on your channel: {CHANNEL_LINK}

    Rules:
    - Keep it very natural and conversational. Don't sound like a bot.
    - Use emojis sparingly (max 1 or 2).
    - MUST include the exact link: {CHANNEL_LINK}
    - Do not use quotes around your response.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        return text if CHANNEL_LINK in text else f"{text} Check here: {CHANNEL_LINK}"
    except:
        return f"Bhai isse achhi deal kal yahan aayi thi, check this out: {CHANNEL_LINK}"

async def start_commenting_bot(worker_info):
    session = worker_info["session"]
    api_id = worker_info["api_id"]
    api_hash = worker_info["api_hash"]
    
    print(f"[*] Worker '{session}' is now monitoring big channels...")
    client = TelegramClient(session, api_id, api_hash)
    await client.start()
    
    @client.on(events.NewMessage(chats=TARGET_CHANNELS))
    async def handler(event):
        # We only comment on messages that have a 'replies' button (Discussion groups)
        if event.message.replies or event.is_group:
            print(f"[*] New message in @{event.chat.username or event.chat_id}! Analyzing...")
            
            # Extract text to provide context
            original_text = event.message.text or "Some image/video deal"
            
            # Wait a bit to look human
            await asyncio.sleep(random.randint(15, 45))
            
            try:
                # Generate AI response
                msg = generate_ai_reply(original_text)
                
                # Reply to the message
                await client.send_message(
                    entity=event.chat_id,
                    message=msg,
                    reply_to=event.message.id
                )
                print(f"[SUCCESS] Hijack Commented: '{msg[:50]}...'")
                
                # Sleep heavily to avoid ban (1 comment per channel per few hours)
                await asyncio.sleep(random.randint(300, 900))
            except Exception as e:
                print(f"[FAILED] Could not comment: {e}")

    print(f"[*] Worker '{session}' listening for events...")
    await client.run_until_disconnected()

async def main():
    # Run multiple workers in parallel
    tasks = [start_commenting_bot(w) for w in WORKERS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
