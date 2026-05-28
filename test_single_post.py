import json
import asyncio
import os
import re
import time
import random
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

def _safe_print(s: str):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", "ignore").decode("ascii"))

def download_image(url: str):
    """Download image locally to avoid Telegram 'Failed to get http url content'."""
    if not url:
        return None
    temp_dir = os.path.join(os.getcwd(), "temp_images")
    os.makedirs(temp_dir, exist_ok=True)
    local_filename = os.path.join(temp_dir, f"temp_{int(time.time())}_{random.randint(100,999)}.jpg")
    headers = {"User-Agent": "Mozilla/5.0"}

    urls_to_try = [url]
    if "media-amazon.com" in url:
        clean_url = re.sub(r"\._[A-Z0-9]+_\.", ".", url)
        if clean_url != url:
            urls_to_try.append(clean_url)

    for target_url in urls_to_try:
        try:
            with requests.get(target_url, headers=headers, stream=True, timeout=15) as r:
                if r.status_code == 200:
                    with open(local_filename, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    return local_filename
        except Exception:
            pass
    return None

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

    _safe_print(f"Attempting to post: {str(product.get('name',''))[:30]}...")
    _safe_print(f"Direct Link: {link}")

    try:
        if image_url:
            local_image = download_image(image_url)
            if local_image:
                with open(local_image, "rb") as f:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=f,
                        caption=msg,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                try:
                    os.remove(local_image)
                except Exception:
                    pass
            else:
                # Fallback to text-only if image download fails
                await bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode='HTML',
                    reply_markup=reply_markup,
                    disable_web_page_preview=False
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode='HTML',
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )
        _safe_print("SUCCESS! Test post sent to your Telegram channel.")
    except Exception as e:
        _safe_print(f"FAILED to post: {e}")

if __name__ == "__main__":
    asyncio.run(test_single_post())
