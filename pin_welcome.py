import asyncio, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

WELCOME_MSG = """🔥 WELCOME TO BUDGET DEALS INDIA 🔥

Yahan SIRF verified loot deals aati hain! 💰

✅ Amazon/Flipkart pe 50-90% OFF wali deals
✅ Under ₹99 ki LOOT items (daily!)  
✅ Price Glitch alerts ⚡
✅ Lightning Deal notifications

📌 RULES:
1️⃣ Notification ON rakho (bell icon dabao)
2️⃣ Jaldi order karo - deals 5-10 min mein khatam ho jaati hain!
3️⃣ Apne dosto ko bhi share karo 🤝

🛒 Pichle hafte ki TOP LOOT:
• ₹1999 ka earphone ₹199 mein gaya!
• ₹599 ki cream ₹49 mein mili!

⚠️ YE CHANNEL FREE HAI - Hum sirf genuine deals share karte hain, koi scam nahi!

Admin: @Shashwat7689
"""

async def pin_welcome():
    bot = Bot(os.getenv("BOT_TOKEN"))
    msg = await bot.send_message(
        chat_id="@budgetdeals_india",
        text=WELCOME_MSG,
        parse_mode=None
    )
    await bot.pin_chat_message(
        chat_id="@budgetdeals_india",
        message_id=msg.message_id,
        disable_notification=True
    )
    print(f"Welcome message PINNED! Message ID: {msg.message_id}")

asyncio.run(pin_welcome())
