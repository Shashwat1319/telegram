import json
import asyncio
import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def test_single_post():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("BOT_TOKEN or CHANNEL_ID not found in .env")
        return

    chat_id = f"@{CHANNEL_ID.replace('@', '')}"
    bot = Bot(token=BOT_TOKEN)

    # Load first product
    with open("product.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        if not data["products"]:
            print("No products in product.json")
            return
        product = data["products"][0]

    # Format message
    name = product.get('name', 'Great Deal!').replace('<', '&lt;').replace('>', '&gt;')
    price = product.get('price', 'Check Link')
    mrp = product.get('mrp', '')
    discount = product.get('discount_percent', '')
    link = product.get('link', '#')
    image_url = product.get('image')

    bachat_str = f"❌ <b>MRP:</b> <strike>{mrp}</strike>\n✅ <b>Loot:</b> <b>{price}</b>"
    if discount:
        bachat_str += f" (<b>{discount} OFF</b>)"

    msg = (
        f"🔥 <b>MASSIVE PRICE DROP DEAL!</b> 🔥\n\n"
        f"🚨 <b>HUGE DISCOUNT DETECTED!</b> 🚨\n\n"
        f"🎁 <b>{name}</b>\n\n"
        f"{bachat_str}\n\n"
        f"⚡ <i>Grab it before the deal expires! Highly recommended budget buy.</i>\n"
        f"⏳ <i>Price kabhi bhi badh sakta hai! Buy FAST!</i> 🏃‍♂️\n\n"
        f"👇 <b>CLAIM THIS DEAL NOW</b> 👇\n"
        f"🛒 <a href='{link}'>Add to Cart (Amazon)</a>\n\n"
        f"👉 Join <b>{chat_id}</b> for more secret loots! 🏃‍♂️"
    )

    share_text = "Bhai%20jaldi%20dekh%2C%20lagta%20hai%20Amazon%20par%20massive%20sale%20aaya%20hai%21%20Sab%20bohot%20saste%20mein%20mil%20raha%20hai.%20Link%20band%20hone%20se%20pehle%20join%20karke%20loot%20le%21%20%F0%9F%98%B1%F0%9F%9A%A8"
    share_url = f"https://t.me/share/url?url=https://t.me/{CHANNEL_ID.replace('@', '')}&text={share_text}"
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 BUY NOW (Amazon)", url=link)],
        [
            InlineKeyboardButton("🔥 Share with Friends", url=share_url),
            InlineKeyboardButton("💰 Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
        ]
    ])

    print(f"Attempting to post: {product.get('name')[:30]}...")
    print(f"Direct Link: {link}")

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
                disable_web_page_preview=False
            )
        print("✅ SUCCESS! Test post sent to your Telegram channel.")
    except Exception as e:
        print(f"❌ Failed to post: {e}")

if __name__ == "__main__":
    asyncio.run(test_single_post())
