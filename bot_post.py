import json
import random
import asyncio
from telegram import Bot
import re
import os

# ---------- Environment variables ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # e.g., @budgetdeals_india

# ---------- Helper function ----------
def escape_md2(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

# ---------- Load products ----------
def load_products():
    with open("products.json", "r") as f:
        return json.load(f)["products"]

# ---------- Generate message ----------
def generate_message(product):
    name = escape_md2(product['name'])
    price = escape_md2(product['price'])
    link = product['link']  # URL must not be escaped

    return (
        f"🔥 *LIMITED TIME DEAL!* 🔥\n\n"
        f"💎 *{name}* अभी सिर्फ **{price}** में!\n"
        f"⏰ Hurry up! Stock सीमित है – खत्म होने से पहले खरीदें!\n"
        f"💸 Best price guaranteed – सिर्फ आज!\n\n"
        f"👉 [Click Here to Grab it Now]({link})\n\n"
        f"✅ जल्दी लें, इस शानदार deal को मिस मत करें!"
    )

# ---------- Post deals ----------
async def post_deals():
    bot = Bot(BOT_TOKEN)
    products = load_products()
    try:
        for i in range(3):
            product = random.choice(products)
            msg = generate_message(product)
            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=msg,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True
                )
                print(f"Posted ({i+1}/3): {product['name']} at {product['price']}")
            except Exception as e:
                print("Error posting:", e)
            await asyncio.sleep(20)  # 20 sec delay between posts
    except asyncio.CancelledError:
        print("Script cancelled manually.")

# ---------- Main ----------
if __name__ == "__main__":
    asyncio.run(post_deals())
