import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Target group for testing visibility (should be an active public group)
TEST_GROUP = "@DealsDiscussion" 

async def debug_visibility():
    # 1. SEND from Account 1
    s1 = os.getenv("TELEGRAM_SESSION_1")
    c1 = TelegramClient(StringSession(s1), int(API_ID), API_HASH)
    
    # 2. CHECK from Account 2
    s2 = os.getenv("TELEGRAM_SESSION_2")
    c2 = TelegramClient(StringSession(s2), int(API_ID), API_HASH)
    
    await c1.connect()
    await c2.connect()
    
    test_msg = f"TEST_VISIBILITY_{os.urandom(4).hex()}"
    print(f"[*] Sending '{test_msg}' from Account 1 to {TEST_GROUP}...")
    
    try:
        sent = await c1.send_message(TEST_GROUP, test_msg)
        print(f"[OK] Message sent! ID: {sent.id}")
        
        await asyncio.sleep(5)
        
        print(f"[*] Checking visibility from Account 2...")
        async for message in c2.iter_messages(TEST_GROUP, limit=10):
            if test_msg in str(message.text):
                print(f"[SUCCESS] Message is VISIBLE to others!")
                break
        else:
            print(f"[FAILURE] Message is NOT visible to Account 2. Account 1 might be SHADOWBANNED or message deleted.")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        
    await c1.disconnect()
    await c2.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_visibility())
