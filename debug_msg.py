import asyncio
import os
from telethon import TelegramClient
from telethon.network import ConnectionTcpObfuscated
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = TelegramClient(
        'userbot_session', 
        int(os.getenv('API_ID')), 
        os.getenv('API_HASH'),
        connection=ConnectionTcpObfuscated
    )
    await client.start()
    ids_to_check = [305, 306]
    print(f"--- Inspecting IDs {ids_to_check} ---")
    
    for mid in ids_to_check:
        m = await client.get_messages('@budgetdeals_india', ids=mid)
        if m:
            print(f"ID: {m.id}")
            print(f"  Type: {type(m)}")
            print(f"  Text: {repr(m.text)}")
            print(f"  Media: {type(m.media) if m.media else 'None'}")
        else:
            print(f"ID: {mid} not found!")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
