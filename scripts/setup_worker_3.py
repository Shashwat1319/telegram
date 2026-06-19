import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

async def setup_worker_3():
    load_dotenv()
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone_3 = os.getenv("PHONE_NUMBER_3")

    if not phone_3:
        print("[ERROR] Please add PHONE_NUMBER_3=+91XXXXXXXXXX to your .env file first!")
        return

    print(f"[*] Setting up Worker 3 using phone: {phone_3}")
    client = TelegramClient("worker_3_session", int(api_id), api_hash)
    
    # This will prompt for OTP in the terminal
    await client.start(phone=phone_3)
    
    print("\n[SUCCESS] Worker 3 Session completely authorized!")
    print("The 'worker_3_session.session' file has been created.")
    print("Now auto_forwarder.py will automatically use this 3rd account to blast deals!")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(setup_worker_3())
