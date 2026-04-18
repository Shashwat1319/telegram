import asyncio, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

async def check():
    bot = Bot(os.getenv("BOT_TOKEN"))
    info = await bot.get_chat("@budgetdeals_india")
    count = await info.get_member_count()
    print(f"Members: {count}")

asyncio.run(check())
