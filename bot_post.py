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
CLEAN_ID = CHANNEL_ID.replace('@', '') if CHANNEL_ID else "channel"

# ---------- Load products ----------
def load_products():
    with open("product.json", "r", encoding="utf-8") as f:
        return json.load(f)["products"]

# ---------- Message Templates ----------
def generate_message(product):
    name = product.get('name', 'Great Deal!')
    price = product.get('price', 'Check Link')
    link = product.get('link', '#')
    
    # Simple clean for HTML special characters
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    
    templates = [
        f"<b>🔥 MEGA LOOT DEAL! 🔥</b>\n\n"
        f"📦 <b>Product:</b> {safe_name}\n"
        f"💰 <b>Price:</b> {price}\n\n"
        f"⚡ <b>Hurry! Price may rise soon!</b>\n"
        f"👉 <a href='{link}'>Grab it now before it's gone!</a>\n\n"
        f"🚀 <i>Deals are flighty, grab 'em while they're hot!</i>\n"
        f"Join <b>@{CLEAN_ID}</b> for more Loot! 💸\n"
        f"#AmazonDeals #Loot #BudgetDeals #IndiaShopping",

        f"<b>🌟 BUDGET PICK OF THE DAY 🌟</b>\n\n"
        f"✅ <b>Best Seller:</b> {safe_name}\n"
        f"💵 <b>Deal Price:</b> {price}\n\n"
        f"✨ <b>Top rated product at lowest price!</b>\n"
        f"🛒 <a href='{link}'>Add to Cart Now</a>\n\n"
        f"🚀 <i>Don't miss out on daily savings!</i>\n"
        f"Join <b>@{CLEAN_ID}</b> for more Loot! 💸\n"
        f"#SmartShopping #DealsIndia #AmazonLoot",

        f"<b>🚨 PRICE DROP ALERT! 🚨</b>\n\n"
        f"📍 <b>Item:</b> {safe_name}\n"
        f"💸 <b>Current Price:</b> {price}\n\n"
        f"📉 <b>Lowest price in the last 24 hours!</b>\n"
        f"🔗 <a href='{link}'>Direct Link to Buy</a>\n\n"
        f"🚀 <i>Deals are flighty, grab 'em while they're hot!</i>\n"
        f"Join <b>@{CLEAN_ID}</b> for more Loot! 💸\n"
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
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode='HTML',
                        reply_markup=reply_markup,
                        disable_web_page_preview=True
                    )
                print(f"Posted: {product['name']}")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Failed to post {product['name']}: {e}")
                
    except Exception as e:
        print(f"Error in posting: {e}")

if __name__ == "__main__":
    asyncio.run(post_deals())
