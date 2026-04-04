import json
import random
import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------- Environment variables ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# ---------- Load products ----------
def load_products():
    with open("product.json", "r", encoding="utf-8") as f:
        return json.load(f)["products"]

# ---------- Message Templates ----------
def generate_message(product):
    name = product.get('name', 'Great Deal!')
    price = product.get('price', 'Check Link')
    link = product.get('link', '#')
    
    templates = [
        f"🔥 *MEGA LOOT DEAL!* 🔥\n\n"
        f"📦 *Product:* {name}\n"
        f"💰 *Price:* {price}\n\n"
        f"⚡ *Hurry! Price may rise soon!*\n"
        f"👉 [Grab it now before it's gone!]({link})\n\n"
        f"🚀 *Deals are flighty, grab 'em while they're hot!*\n"
        f"Join **@budgetdeals_india** for more Loot! 💸\n"
        f"#AmazonDeals #Loot #BudgetDeals #IndiaShopping",

        f"🌟 *BUDGET PICK OF THE DAY* 🌟\n\n"
        f"✅ *Best Seller:* {name}\n"
        f"💵 *Deal Price:* {price}\n\n"
        f"✨ *Top rated product at lowest price!*\n"
        f"🛒 [Add to Cart Now]({link})\n\n"
        f"🚀 *Don't miss out on daily savings!*\n"
        f"Join **@budgetdeals_india** for more Loot! 💸\n"
        f"#SmartShopping #DealsIndia #AmazonLoot",

        f"🚨 *PRICE DROP ALERT!* 🚨\n\n"
        f"📍 *Item:* {name}\n"
        f"💸 *Current Price:* {price}\n\n"
        f"📉 *Lowest price in the last 24 hours!*\n"
        f"🔗 [Direct Link to Buy]({link})\n\n"
        f"🚀 *Deals are flighty, grab 'em while they're hot!*\n"
        f"Join **@budgetdeals_india** for more Loot! 💸\n"
        f"#PriceDrop #LootDeals #AmazonIndia"
    ]
    return random.choice(templates)

# ---------- Post deals ----------
async def post_deals():
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    bot = Bot(BOT_TOKEN)
    products = load_products()
    
    try:
        # Post the top 3 (newest) products found
        for i in range(min(3, len(products))):
            product = products[i]
            msg = generate_message(product)
            image_url = product.get('image')
            
            try:
                if image_url:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=msg,
                        parse_mode='Markdown'
                    )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode='Markdown'
                    )
                print(f"Posted ({i+1}/3): {product['name']}")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Failed to post {product['name']}: {e}")
                
    except Exception as e:
        print(f"Error in posting: {e}")

if __name__ == "__main__":
    asyncio.run(post_deals())
