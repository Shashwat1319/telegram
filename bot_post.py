import json
import random
import asyncio
from telegram import Bot
import os

# ---------- Environment variables ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # e.g., @budgetdeals_india

# ---------- Load products ----------
def load_products():
    with open("product.json", "r") as f:
        return json.load(f)["products"]

# ---------- Templates ----------
def template_1(name, price, link):
    return (
        f"🔥 TODAY'S BEST DEAL 🔥\n\n"
        f"💰 Price Drop Alert!\n"
        f"👉 {name} अब सिर्फ {price}\n\n"
        f"⭐ Highlights:\n"
        f"• High demand item\n"
        f"• Budget-friendly\n"
        f"• Limited-time discount\n\n"
        f"🔗 Deal Link: {link}\n\n"
        f"⚠️ Price कभी भी बढ़ सकता है — अभी ले लो।"
    )

def template_2(name, price, link):
    return (
        f"⚡ LIMITED TIME OFFER ⚡\n\n"
        f"🛍️ Product: {name}\n"
        f"💵 Offer Price: {price}\n\n"
        f"🔥 Why grab it now?\n"
        f"• Massive price drop\n"
        f"• Trusted Amazon delivery\n"
        f"• Stock selling fast\n\n"
        f"👉 Buy Now: {link}\n\n"
        f"⏳ Hurry! Deal live for a short time only."
    )

def template_3(name, price, link):
    return (
        f"💥 STEAL DEAL ALERT! 💥\n\n"
        f"🎯 {name}\n"
        f"💸 Current Price: {price}\n\n"
        f"✨ Benefits:\n"
        f"• Value for money\n"
        f"• Best seller item\n"
        f"• Fast shipping available\n\n"
        f"🔗 Direct Purchase Link: {link}\n\n"
        f"🚨 Do not miss it — deals like this do not stay long!"
    )

# List of templates
TEMPLATES = [template_1, template_2, template_3]

# ---------- Generate message (random template) ----------
def generate_message(product):
    name = product['name']
    price = product['price']
    link = product['link']

    chosen_template = random.choice(TEMPLATES)
    return chosen_template(name, price, link)

# ---------- Post deals ----------
async def post_deals():
    bot = Bot(BOT_TOKEN)
    products = load_products()
    try:
        # Post the top 3 (newest) products found
        for i in range(min(3, len(products))):
            product = products[i]
            msg = generate_message(product)
            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=msg,
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
