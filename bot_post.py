import json
import random
import asyncio
import os
import re
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# ---------- Helper for Price Parsing ----------
def get_price_value(price_str):
    try:
        clean = re.sub(r'[^\d.]', '', str(price_str))
        return float(clean) if clean else 999999.0
    except:
        return 999999.0

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
def generate_message(product, is_lightning=False):
    name = product.get('name', 'Great Deal!')
    price = product.get('price', 'Check Link')
    link = product.get('link', '#')
    category = product.get('category', 'Loot')
    
    # Simple clean for HTML special characters
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    
    # Identify Ladies Categories for special branding
    ladies_cats = ["Ladies Fashion", "Ladies Shoes", "Ladies Jewelry", "Beauty", "Personal Care"]
    is_ladies = any(c in category for c in ladies_cats)
    
    header_extra = ""
    footer_extra = ""
    if is_ladies:
        header_extra = "💃 <b>LADIES SPECIAL LOOT</b> 💃\n"
        footer_extra = "\n✨ <i>Special deal for the queens!</i> 👜💄"
        
    if is_lightning:
        header_extra = "⚡️ <b>LIGHTNING DEAL OF THE HOUR</b> ⚡️\n"
        footer_extra = "\n⏳ <i>Highest discount pinned! Buy before it expires!</i> 🏃‍♂️"

    if is_ladies:
        templates = [
            f"{header_extra}🎀 <b>PREMIUM FASHION LOOT - 80% OFF!</b> 🎀\n\n"
            f"👜 <b>{safe_name}</b>\n"
            f"✨ <b>Exclusive Price:</b> <b>{price}</b> 💎\n\n"
            f"💁‍♀️ <i>Upgrade your style without breaking the bank! Quality guaranteed.</i>{footer_extra}\n"
            f"👇 <b>CLAIM THIS STYLE NOW</b> 👇\n"
            f"🛍️ <a href='{link}'>Shop the Collection</a>\n\n"
            f"🤫 <b>Limited Stock!</b> Share with your besties! 👯‍♀️\n"
            f"👉 Join <b>@{CLEAN_ID}</b> for more premium drops! 👑",

            f"{header_extra}💄 <b>BEAUTY GLITCH: PRICE SLASHED!</b> 💄\n\n"
            f"🌟 <b>{safe_name}</b>\n"
            f"🔥 <b>Special Deal:</b> <b>{price}</b> 😱\n\n"
            f"✨ <i>Look stunning, spend less! Grab it before the price goes back up.</i>{footer_extra}\n"
            f"🛒 <a href='{link}'>Add to Cart - Fast!</a>\n\n"
            f"📢 <b>Forward to your girl gang!</b> Don't let them miss this! 💖\n"
            f"Join <b>@{CLEAN_ID}</b> for daily beauty steals!",

            f"{header_extra}🛑 <b>HIDDEN DEAL - FOR LADIES ONLY!</b> 🛑\n\n"
            f"👠 <b>{safe_name}</b>\n"
            f"💎 <b>Grab it for:</b> <b>{price}</b> ✅\n\n"
            f"⚡️ <i>Ye deal miss nahi honi chahiye! Direct link niche hai.</i>{footer_extra}\n"
            f"🔗 <a href='{link}'>Direct Link to Loot</a>\n\n"
            f"🚀 <i>Hum aise secret Ladies Loot daily post karte hain!</i>\n"
            f"Join <b>@{CLEAN_ID}</b> fast before stock ends! ⏳"
        ]
    else:
        templates = [
            f"{header_extra}🚨 <b>ERROR PRICING? SYSTEM GLITCH!</b> 🚨\n\n"
            f"🎁 <b>{safe_name}</b>\n"
            f"💥 <b>Current Price:</b> <b>{price}</b> 😱\n\n"
            f"⚠️ <i>Only active for next 5-10 minutes before Amazon fixes it!</i>{footer_extra}\n"
            f"👇 <b>CLICK HERE & ADD TO CART FAST</b> 👇\n"
            f"🛒 <a href='{link}'>Claim GLITCH Deal Now</a>\n\n"
            f"🤫 <b>DO NOT SHARE ON FACEBOOK/INSTA!</b> Forward only to close friends!\n"
            f"👉 Join <b>@{CLEAN_ID}</b> to get these secret deals first! 🏃‍♂️",

            f"{header_extra}😱 <b>PRICE DROP OF THE MONTH! 99% CLAIMED!</b> 😱\n\n"
            f"📦 <b>{safe_name}</b>\n"
            f"🔥 <b>Loot Price:</b> <b>{price}</b> 📉\n\n"
            f"⏳ <i>Stock will end completely in any second! Just 3 pieces left!</i>{footer_extra}\n"
            f"🛒 <a href='{link}'>Click Here To Buy</a>\n\n"
            f"💵 Company ka loss aapka profit! Jaldi join kar lo: <b>@{CLEAN_ID}</b>\n"
            f"📢 <b>Apne dosto ko jaldi share karo, unhe bhi lootne do!</b>",

            f"{header_extra}🛑 <b>SECRET LINK - WILL BE DELETED SOON!</b> 🛑\n\n"
            f"🌟 <b>{safe_name}</b>\n"
            f"💎 <b>Get It Only At:</b> <b>{price}</b> ✅\n\n"
            f"⚡️ <i>Ye price wapas zindagi mein nahi aayega! Guarantee.</i>{footer_extra}\n"
            f"🔗 <a href='{link}'>Direct Hidden Link to Buy</a>\n\n"
            f"🚀 <i>Hum aise secret Loot daily post karte hain!</i>\n"
            f"Join <b>@{CLEAN_ID}</b> fast before we make the channel private! 🔒\n"
            f"💬 <b>Forward kro groups me taaki price badhne se pehle baki bhi le sake!</b>"
        ]
    msg = random.choice(templates)
    
    # Telegram Search SEO Hack: Hiding high-traffic keywords so the post ranks globally without looking ugly
    seo_block = (
        "\n\n<tg-spoiler>"
        "🏷️ Tags: #AmazonDeals #LootDealsIndia #FlipkartSale #BudgetShopping #Offers #LowestPrice #FreeShopping\n"
        "🔎 Search Keywords: best mobile exchange offer, amazon laptop sale today, cheapest deals under 99, 99 store flipkart, free sample products, secret tricks, price drop alerts india"
        "</tg-spoiler>"
    )
    return msg + seo_block

# ---------- Post deals ----------
async def post_deals():
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    bot = Bot(BOT_TOKEN)
    products = load_products()

    try:
        import sys
        random_mode = len(sys.argv) > 1 and sys.argv[1] == "--random"
        
        if random_mode and len(products) > 3:
            # Pick 2 random products from history to keep channel active
            num_to_post = min(2, len(products))
            products_to_post = random.sample(products, num_to_post)
            print(f"Fallback mode: Selected {num_to_post} random products.")
        else:
            # Post the top 3 (newest) products found
            num_to_post = min(3, len(products))
            products_to_post = products[:num_to_post]
            print(f"Normal mode: Selected top {num_to_post} newest products.")

        # Identify the cheapest item in this batch to be the "Lightning Deal"
        cheapest_product = None
        if products_to_post:
            cheapest_product = min(products_to_post, key=lambda p: get_price_value(p.get('price', '999999')))

        for product in products_to_post:
            is_lightning = (product == cheapest_product)
            msg = generate_message(product, is_lightning=is_lightning)
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
                sent_msg = None
                if image_url:
                    try:
                        sent_msg = await bot.send_photo(
                            chat_id=chat_id,
                            photo=image_url,
                            caption=msg,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    except Exception as photo_e:
                        print(f"Photo upload failed ({photo_e}). Falling back to Text-only message...")
                        sent_msg = await bot.send_message(
                            chat_id=chat_id,
                            text=msg,
                            parse_mode='HTML',
                            reply_markup=reply_markup,
                            disable_web_page_preview=False
                        )
                else:
                    sent_msg = await bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode='HTML',
                        reply_markup=reply_markup,
                        disable_web_page_preview=False
                    )
                
                product_name = product.get('name', 'Product').encode('ascii', 'ignore').decode('ascii')
                print(f"Posted: {product_name}")
                
                # Auto-pin the lightning deal
                if is_lightning and sent_msg:
                    try:
                        await bot.pin_chat_message(chat_id=chat_id, message_id=sent_msg.message_id, disable_notification=False)
                        print(f"Pinned lightning deal: {product_name}")
                    except Exception as pin_err:
                        print(f"Could not pin message (check admin rights): {str(pin_err).encode('ascii', 'ignore').decode('ascii')}")
                        
                await asyncio.sleep(5)
            except Exception as e:
                err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"Failed to post {product_name}: {err_msg}")
                
    except Exception as e:
        err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"Error in posting: {err_msg}")

if __name__ == "__main__":
    asyncio.run(post_deals())
