import json
import random
import asyncio
import os
import re
import requests
from urllib.parse import quote
from datetime import datetime
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
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "")

# ---------- Constants & Counter ----------
COUNTER_FILE = "post_count.txt"

def get_post_count():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def increment_post_count():
    count = get_post_count() + 1
    with open(COUNTER_FILE, "w") as f:
        f.write(str(count))
    return count

def reset_post_count():
    with open(COUNTER_FILE, "w") as f:
        f.write("0")

# ---------- Load products ----------
def load_products():
    with open("product.json", "r", encoding="utf-8") as f:
        return json.load(f)["products"]

# ---------- Message Templates ----------
def generate_message(product, is_lightning=False):
    name = product.get('name', 'Great Deal!')
    
    # Robust price formatting
    raw_price = str(product.get('price', 'Check Link'))
    raw_mrp = str(product.get('mrp', ''))
    discount = str(product.get('discount_percent', ''))

    def format_price(p):
        if not p or 'Check' in p: return ""
        ascii_p = p.encode('ascii', 'ignore').decode('ascii').strip()
        ascii_p = re.sub(r'[^\d.,\- ]', '', ascii_p).strip()
        if not ascii_p: return ""
        if ' - ' in ascii_p:
            l, r = ascii_p.split(' - ', 1)
            return f"₹{l.strip().strip(',.')} - ₹{r.strip().strip(',.')}"
        return f"₹{ascii_p.strip().strip(',.')}"

    price = format_price(raw_price) or "Check Link"
    mrp = format_price(raw_mrp)
    
    link = product.get('link', '#')
    if CLICK_TRACKER_URL:
        link = f"{CLICK_TRACKER_URL}/go?url={quote(link)}"
        
    category = product.get('category', 'Loot')
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    
    # Formatting the "Bachat" (Savings) string
    bachat_str = ""
    if mrp and price != "Check Link":
        bachat_str = f"❌ <b>MRP:</b> <strike>{mrp}</strike>\n✅ <b>Deal Price:</b> <b>{price}</b>"
        if discount:
            bachat_str += f" (<b>{discount} Instant Savings</b>)"
    else:
        bachat_str = f"💰 <b>Special Price:</b> <b>{price}</b>"

    header_extra = "✨ <b>VERIFIED BUDGET DEAL</b> ✨\n"
    footer_extra = ""
    if is_lightning or (discount and any(x in discount for x in ['50%', '60%', '70%', '80%', '90%'])):
        header_extra = "🔥 <b>TOP-RATED FLASH DEAL!</b> 🔥\n"
        footer_extra = "\n⚠️ <i>Note: Lightning deals expire quickly. Check price on Amazon.</i>"

    templates = [
        # 1. Smart Shopper Style
        f"{header_extra}\n"
        f"📦 <b>{safe_name}</b>\n\n"
        f"{bachat_str}\n\n"
        f"⭐️ <i>Highly rated product identified by our budget tracker. Best price currently available.</i>{footer_extra}\n\n"
        f"🛒 <a href='{link}'>View Deal & Order (Amazon)</a>\n\n"
        f"📍 <i>Join @{CLEAN_ID} for genuine price drop alerts only!</i>",

        # 2. Daily Pick Style
        f"{header_extra}\n"
        f"🎁 <b>OUR TOP PICK TODAY!</b>\n\n"
        f"<b>Product:</b> {safe_name}\n"
        f"{bachat_str}\n\n"
        f"✅ <i>Verified seller and genuine discount. Quality checked.</i>{footer_extra}\n\n"
        f"🚀 <a href='{link}'>Click here to Grab this Deal</a>\n\n"
        f"🤝 <i>Share with friends who need this! @{CLEAN_ID}</i>"
    ]
    msg = random.choice(templates)
    
    seo_block = (
        "\n\n<tg-spoiler>"
        "🏷️ #AmazonIndia #VerifiedDeals #SmartShopping #BudgetDeals #IndiaOffers"
        "</tg-spoiler>"
    )
    return msg + seo_block

# ---------- Viral Share Challenge ----------
def generate_viral_message():
    tg_link = f"https://t.me/{CLEAN_ID}"
    share_text = "Bhai%20jaldi%20dekh%2C%20lagta%20hai%20Amazon%20par%20massive%20sale%20aaya%20hai%21%20Sab%20bohot%20saste%20mein%20mil%20raha%20hai.%20Link%20band%20hone%20se%20pehle%20join%20karke%20loot%20le%21%20%F0%9F%98%B1%F0%9F%9A%A8"
    share_url = f"https://t.me/share/url?url={tg_link}&text={share_text}"

    templates = [
        f"🔥 <b>MEMBERS ONLY MEGA LOOT UNLOCKED!</b> 🔥\n\n"
        f"Bhaiyo, agla <b>Top Discount Deal</b> aane wala hai, lekin ye sirf unhe dikhega jo hamare active supportive members hain! 😍\n\n"
        f"✅ <b>Mission:</b> Is link ko apne <b>5 Groups</b> mein forward karo aur Loot link ka access paao!\n\n"
        f"👇 <b>CLICK TO SHARE & GET ACCESS</b> 👇\n"
        f"🚀 <a href='{share_url}'>Click here to Share with Friends</a>\n\n"
        f"🤫 <i>1000 members hote hi Mega Price Drop activate hoga!</i>",

        f"🎁 <b>EXCLUSIVE GIVEAWAY & LOOT ALERT!</b> 🎁\n\n"
        f"Amazon par massive price crash detected! Hum iska direct loot link tabhi post karenge jab channel mein <b>1000 Members</b> pure honge! 🏃‍♂️\n\n"
        f"📢 <b>Helping Hand:</b> Jaldi se 5 dosto ko ye channel share karo taaki hum turant link de sakein!\n\n"
        f"🔗 <a href='{share_url}'>Share and Join (Click Here)</a>\n\n"
        f"✅ <i>JITNI JALDI SHARE, UTNI JALDI LOOT!</i>"
    ]
    return random.choice(templates)

# ---------- Interactive Polls ----------
async def send_automated_poll(bot, chat_id):
    question = "Bhaiyo, aapko sabse zyada deals kis category mein chahiye? 🔥"
    options = [
        "📱 Mobiles & Accessories",
        "👟 Shoes & Fashion",
        "🎧 Earphones & Gadgets",
        "🏠 Kitchen & Home Appliances",
        "🧴 Beauty & Personal Care"
    ]
    try:
        print(f"[*] Sending Automated Poll to {chat_id}...")
        await bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=True,
            allows_multiple_answers=True
        )
        return True
    except Exception as e:
        print(f"Failed to send poll: {e}")
        return False

# ---------- Amazon Bounties ----------
def generate_bounty_message():
    aff_id = os.getenv("AFFILIATE_ID_IN", "budgetdeals-21")
    
    bounties = [
        {
            "name": "Amazon Prime FREE Trial",
            "url": f"https://www.amazon.in/tryprime?tag={aff_id}",
            "desc": f"🚀 <b>Join Amazon Prime for FREE!</b>\n\nGet FREE 1-Day Delivery, early access to lightning deals, and Prime Video access.\n\n✨ <b>Membership Benefits:</b>\n✅ Free Delivery on All Orders\n✅ Prime Music & Video\n✅ Exclusive Member Deals\n\n👉 <b>Join Now (Free Trial):</b> https://www.amazon.in/tryprime?tag={aff_id}"
        },
        {
            "name": "Amazon Business (GST Invoice)",
            "url": f"https://www.amazon.in/tryab?tag={aff_id}",
            "desc": f"💼 <b>Save 28% Extra with GST Invoice!</b>\n\nRegister your Business Account for FREE and get exclusive business pricing and GST claims on every purchase.\n\n✨ <b>Best for Resellers & Shop Owners!</b>\n👉 <b>Register Free Account:</b> https://www.amazon.in/tryab?tag={aff_id}"
        },
        {
            "name": "Audible 90-Days Free",
            "url": f"https://www.amazon.in/dp/B077S5CVYQ?tag={aff_id}",
            "desc": f"🎧 <b>Listen to 100,000+ Audiobooks for FREE!</b>\n\nGet 90 days of Audible membership for absolutely zero cost. Perfect for learning and entertainment.\n\n👉 <b>Claim 90-Day Free Trial:</b> https://www.amazon.in/dp/B077S5CVYQ?tag={aff_id}"
        }
    ]
    selected = random.choice(bounties)
    return selected["desc"]

# ---------- Post deals ----------
async def post_deals():
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    bot = Bot(token=BOT_TOKEN)

    products = load_products()
    if not products:
        print("No products to post. Checking for Bounty...")
        bounty_msg = generate_bounty_message()
        await bot.send_message(chat_id=chat_id, text=bounty_msg, parse_mode='HTML')
        return

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

        # Check for Interval Tasks (Viral Hooks / Bounties / Polls)
        current_count = increment_post_count()
        
        # Poll triggering (Every 15 posts)
        if current_count % 15 == 0:
            await send_automated_poll(bot, chat_id)

        # Viral/Bounty Interval (Every 10-15 posts to maintain trust)
        viral_interval = random.randint(10, 15)
        if current_count >= viral_interval:
            print(f"Post count: {current_count}. Triggering Growth Cycle!")
            # Pick between Viral Message or Bounty
            if random.random() > 0.5:
                growth_msg = generate_viral_message()
            else:
                growth_msg = generate_bounty_message()
                
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=growth_msg,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                reset_post_count() # Reset main interval counter
            except Exception as growth_e:
                print(f"Failed to post growth hook: {growth_e}")

        # Identify the cheapest item in this batch to be the "Lightning Deal"
        cheapest_product = None
        if products_to_post:
            cheapest_product = min(products_to_post, key=lambda p: get_price_value(p.get('price', '999999')))

        for product in products_to_post:
            is_lightning = (product == cheapest_product)
            msg = generate_message(product, is_lightning=is_lightning)
            image_url = product.get('image')
            link = product.get('link', '#')
            
            # Using balanced Hindi text context designed for viral sharing!
            share_text = "Bhai%20jaldi%20dekh%2C%20lagta%20hai%20Amazon%20par%20massive%20sale%20aaya%20hai%21%20Sab%20bohot%20saste%20mein%20mil%20raha%20hai.%20Link%20band%20hone%20se%20pehle%20join%20karke%20loot%20le%21%20%F0%9F%98%B1%F0%9F%9A%A8"
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
