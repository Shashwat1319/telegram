import json
import random
import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

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
    
    # Clean name for Markdown (escaping special characters if needed, or just keep simple)
    clean_name = name.replace('*', '').replace('_', '')
    
    templates = [
        f"🔥 *MEGA LOOT DEAL!* 🔥\n\n"
        f"📦 *Product:* {clean_name}\n"
        f"💰 *Price:* {price}\n\n"
        f"⚡ *Hurry! Price may rise soon!*\n"
        f"👉 [Grab it now before it's gone!]({link})\n\n"
        f"🚀 *Deals are flighty, grab 'em while they're hot!*\n"
        f"Join **@{CHANNEL_ID}** for more Loot! 💸\n"
        f"#AmazonDeals #Loot #BudgetDeals #IndiaShopping",

        f"🌟 *BUDGET PICK OF THE DAY* 🌟\n\n"
        f"✅ *Best Seller:* {clean_name}\n"
        f"💵 *Deal Price:* {price}\n\n"
        f"✨ *Top rated product at lowest price!*\n"
        f"🛒 [Add to Cart Now]({link})\n\n"
        f"🚀 *Don't miss out on daily savings!*\n"
        f"Join **@{CHANNEL_ID}** for more Loot! 💸\n"
        f"#SmartShopping #DealsIndia #AmazonLoot",

        f"🚨 *PRICE DROP ALERT!* 🚨\n\n"
        f"📍 *Item:* {clean_name}\n"
        f"💸 *Current Price:* {price}\n\n"
        f"📉 *Lowest price in the last 24 hours!*\n"
        f"🔗 [Direct Link to Buy]({link})\n\n"
        f"🚀 *Deals are flighty, grab 'em while they're hot!*\n"
        f"Join **@{CHANNEL_ID}** for more Loot! 💸\n"
        f"#PriceDrop #LootDeals #AmazonIndia"
    ]
    return random.choice(templates)

# ---------- Post deals ----------
async def post_deals():
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    bot = Bot(BOT_TOKEN)
    products = load_products()
    
    # Growth button
    share_url = f"https://t.me/share/url?url=https://t.me/{CHANNEL_ID.replace('@', '')}&text=Check%20out%20these%20amazing%20deals!"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Share with Friends", url=share_url)]
    ])
    
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
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                print(f"Posted ({i+1}/3): {product['name']}")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Failed to post {product['name']}: {e}")
                
    except Exception as e:
        print(f"Error in posting: {e}")

if __name__ == "__main__":
    asyncio.run(post_deals())
