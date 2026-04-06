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
        f"🚨 <b>ERROR PRICING? SYSTEM GLITCH!</b> 🚨\n\n"
        f"🎁 <b>{safe_name}</b>\n"
        f"💥 <b>Current Price:</b> <b>{price}</b> 😱\n\n"
        f"⚠️ <i>Only active for next 5-10 minutes before Amazon fixes it!</i>\n"
        f"👇 <b>CLICK HERE & ADD TO CART FAST</b> 👇\n"
        f"🛒 <a href='{link}'>Claim GLITCH Deal Now</a>\n\n"
        f"🤫 <b>DO NOT SHARE ON FACEBOOK/INSTA!</b> Forward only to close friends!\n"
        f"👉 Join <b>@{CLEAN_ID}</b> to get these secret deals first! 🏃‍♂️",

        f"😱 <b>PRICE DROP OF THE MONTH! 99% CLAIMED!</b> 😱\n\n"
        f"📦 <b>{safe_name}</b>\n"
        f"🔥 <b>Loot Price:</b> <b>{price}</b> 📉\n\n"
        f"⏳ <i>Stock will end completely in any second! Just 3 pieces left!</i>\n"
        f"🛒 <a href='{link}'>Click Here To Buy</a>\n\n"
        f"💵 Company ka loss aapka profit! Jaldi join kar lo: <b>@{CLEAN_ID}</b>\n"
        f"📢 <b>Apne dosto ko jaldi share karo, unhe bhi lootne do!</b>",

        f"🛑 <b>SECRET LINK - WILL BE DELETED SOON!</b> 🛑\n\n"
        f"🌟 <b>{safe_name}</b>\n"
        f"💎 <b>Get It Only At:</b> <b>{price}</b> ✅\n\n"
        f"⚡️ <i>Ye price wapas zindagi mein nahi aayega! Guarantee.</i>\n"
        f"🔗 <a href='{link}'>Direct Hidden Link to Buy</a>\n\n"
        f"🚀 <i>Hum aise secret Loot daily post karte hain!</i>\n"
        f"Join <b>@{CLEAN_ID}</b> fast before we make the channel private! 🔒\n"
        f"💬 <b>Forward kro groups me taaki price badhne se pehle baki bhi le sake!</b>"
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
            link = product.get('link', '#')
            
            # Using extreme Hindi text context designed for viral sharing! "Bhai jaldi dekh, lagta hai Amazon mein koi Glitch aaya hai! Sab ekdam free jaisa mil raha hai. Link band hone se pehle join karke loot le! 😱🚨"
            share_text = "Bhai%20jaldi%20dekh%2C%20lagta%20hai%20Amazon%20mein%20koi%20Glitch%20aaya%20hai%21%20Sab%20ekdam%20free%20jaisa%20mil%20raha%20hai.%20Link%20band%20hone%20se%20pehle%20join%20karke%20loot%20le%21%20%F0%9F%98%B1%F0%9F%9A%A8"
            share_url = f"https://t.me/share/url?url=https://t.me/{CHANNEL_ID.replace('@', '')}&text={share_text}"
            
            reply_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🛒 BUY NOW (Amazon)", url=link)
                ],
                [
                    InlineKeyboardButton("🔥 Share with Friends", url=share_url),
                    InlineKeyboardButton("💰 Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
                ]
            ])
            
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
