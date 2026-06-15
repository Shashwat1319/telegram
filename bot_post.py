# -*- coding: utf-8 -*-
import json
import time
import random
import asyncio
import os
import re
import aiohttp
from urllib.parse import urlparse, quote
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from functools import lru_cache

# ---------- Helper for Price Parsing ----------
def get_price_value(price_str):
    try:
        clean = re.sub(r'[^\d.]', '', str(price_str))
        return float(clean) if clean else 999999.0
    except:
        return 999999.0

# Load environment variables
load_dotenv()

# ---------- Image Downloader ----------
async def is_url_accessible(url: str) -> bool:
    """Check if a URL is reachable using aiohttp.
    Amazon URLs are assumed reachable.
    """
    if "amazon." in url:
        return True
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=5) as resp:
                return resp.status < 400 or resp.status in (403, 405, 503)
    except Exception:
        return False

async def download_image(url: str) -> str | None:
    """Download image asynchronously and cache it.
    Returns the local file path or None.
    """
    if not url:
        return None
    if not await is_url_accessible(url):
        print(f"[WARN] Image URL unreachable, skipping download: {url}")
        return None
    cache_dir = os.path.join(os.getcwd(), "image_cache")
    os.makedirs(cache_dir, exist_ok=True)
    # Use SHA1 hash of URL as filename
    import hashlib
    filename = hashlib.sha1(url.encode('utf-8')).hexdigest() + ".jpg"
    local_path = os.path.join(cache_dir, filename)
    if os.path.exists(local_path):
        return local_path
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    urls_to_try = [url]
    if "media-amazon.com" in url:
        clean_url = re.sub(r'\._[A-Z0-9]+_\.', '.', url)
        if clean_url != url:
            urls_to_try.append(clean_url)
    async with aiohttp.ClientSession(headers=headers) as session:
        for target_url in urls_to_try:
            try:
                async with session.get(target_url, timeout=15) as resp:
                    if resp.status == 200:
                        with open(local_path, 'wb') as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                f.write(chunk)
                        return local_path
                    else:
                        print(f"[RETRY-INFO] Image URL failed {resp.status}: {target_url}")
            except Exception as e:
                print(f"[RETRY-INFO] Error downloading image {target_url}: {e}")
    return None

# ---------- Environment variables ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CLEAN_ID = CHANNEL_ID.replace('@', '') if CHANNEL_ID else "channel"
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "")
CLICK_TRACKER_FUNC = f"{CLICK_TRACKER_URL}/.netlify/functions/go" if CLICK_TRACKER_URL else ""
# New configuration variables
POST_INTERVAL_MINUTES = int(os.getenv("POST_INTERVAL_MINUTES", "30"))
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID")  # optional
DYNAMIC_GAP_MIN = int(os.getenv("DYNAMIC_GAP_MIN", "12"))
DYNAMIC_GAP_MAX = int(os.getenv("DYNAMIC_GAP_MAX", "24"))

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
@lru_cache(maxsize=1)
def load_products():
    with open("product.json", "r", encoding="utf-8") as f:
        return json.load(f)["products"]

# ---------- Message Templates ----------
POST_TEMPLATES = [
    lambda product, count=0: generate_message(product, post_count=count),
    # Placeholder for future A/B variants
]

def generate_message(product, post_count=0):
    name = product.get('name', 'Great Deal!')
    # Robust price formatting
    raw_price = str(product.get('price', 'Check Link'))
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
    link = product.get('link', '#')
    if CLICK_TRACKER_URL and not any(x in link.lower() for x in ["amazon.", "amzn.to"]):
        link = f"{CLICK_TRACKER_FUNC}?url={quote(link)}"
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    hook = product.get('hook', 'Bhai ye loot miss mat karna! 😱')
    pain = product.get('pain', 'Hostel me aisi cheeze roz roz nahi milti.')
    fix = product.get('fix', f"Ye solid deal hai, abhi order kar lo.")
    loot_reason = product.get('loot_reason', '')
    rating = product.get('rating', '')
    proof_str = f"⭐ <b>Rating:</b> {rating}" if rating and rating != "Not specified" else ""
    loot_block = f"📉 <b>Loot Reason:</b> {loot_reason}\n" if loot_reason else ""
    # Calculate price drop %
    try:
        p_val = get_price_value(product.get('price', '0'))
        m_val = get_price_value(product.get('mrp', '0'))
        if m_val > p_val:
            drop = int(((m_val - p_val) / m_val) * 100)
            badge = f"🔥 <b>PRICE DROP: {drop}% OFF</b>\n\n"
        else:
            badge = "🚀 <b>LIMITED TIME DEAL</b>\n\n"
    except:
        badge = "⚡ <b>HOT DEAL</b>\n\n"
    templates = [
        # Format A: Direct deal
        f"{badge}" f"🔥 <b>{safe_name[:60]}</b>\n\n" f"💸 <b>Price:</b> {price}\n" f"✔️ <b>Why:</b> {fix}\n" f"⏰ <b>Deal:</b> Limited stock — price can go up anytime!\n",
        # Format B: Pain → Solution
        f"{badge}" f"😤 {pain}\n\n" f"✅ <b>Solution:</b> {safe_name[:50]}\n" f"💸 <b>Price:</b> {price}\n" f"✔️ {fix}\n" f"⏰ <b>Grab it before price hike!</b>\n",
        # Format C: Review style
        f"{badge}" f"⭐ <b>Today's Best Deal</b>\n\n" f"📦 <b>{safe_name[:55]}</b>\n" f"💸 <b>Price:</b> {price}\n" f"✔️ {fix}\n" f"⏰ Limited time offer!\n",
    ]
    msg = templates[post_count % len(templates)]
    if proof_str:
        msg += f"{proof_str}\n\n"
    else:
        msg += "\n"
    current_time = datetime.now().strftime('%I:%M %p')
    msg += (
        f"🔗 <a href='{link}'><b>BUY BEFORE PRICE GOES UP 👇</b></a>\n\n"
        f"✅ <i>Verified Active at {current_time} IST</i>\n"
        f"📢 <i>Join @{CLEAN_ID} for more secret student loots!</i>"
    )
    seo_block = (
        "\n\n<tg-spoiler>"
        "🏷️ #LootDeals #StudentHacks #AmazonSale #BudgetFinds"
        "</tg-spoiler>"
    )
    return msg + seo_block

# ---------- Viral Share Challenge ----------
def generate_viral_message():
    tg_link = f"https://t.me/{CLEAN_ID}"
    share_text = "Bhai%20jaldi%20dekh%2C%20lagta%20hai%20Amazon%20par%20massive%20sale%20aaya%20hai%21%20Sab%20bohot%20saste%20mein%20mil%20raha%20hai.%20Link%20band%20hone%20se%20pehle%20join%20karke%20loot%20le%21%20%F0%9F%98%B1%F0%9F%9A%A8"
    share_url = f"https://t.me/share/url?url=https://t.me/{CHANNEL_ID.replace('@', '')}&text={share_text}"
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

# ---------- Authority Posts (Non-Selling) ----------
def generate_authority_post():
    posts = [
        "📚 <b>3 cheeze jo hostel me avoid karo padhai ke time:</b>\n\n1. Bed pe padhna (Neend aayegi 100%)\n2. Dosto ke samne room khula rakhna\n3. Mess jane ke turant baad padhna baithna (Food coma)\n\n<i>Table aur chair pe focus double hota hai. Try karke dekho.</i>",
        "💡 <b>Quick Hack:</b> Agar phone bohot distract kar raha hai, toh screen ko 'Grayscale' (Black & White) mode me daal do. \n\nInsta/Reels ka dopamine 50% gir jayega aur phone use karne ka mann kam karega. Try it right now!",
        "💸 <b>Budgeting Rule for Students: 50-30-20</b>\n\n- 50% zaroori kharcha (Rent, Mess)\n- 30% wants (Movie, Bahar ka khana)\n- 20% save karo (Emergencies ke liye)\n\n<i>Pocket money kitni bhi ho, saving aadat se aati hai.</i>"
    ]
    return random.choice(posts)

# ---------- Amazon Bounties ----------
def generate_bounty_message():
    aff_id = os.getenv("AFFILIATE_ID_IN", "shashwat022-21")
    bounties = [
        {
            "name": "Amazon Prime FREE Trial",
            "url": f"https://www.amazon.in/tryprime?tag={aff_id}",
            "desc": "🚀 <b>Join Amazon Prime for FREE!</b>\n\nGet FREE 1-Day Delivery, early access to lightning deals, and Prime Video access.\n\n✨ <b>Membership Benefits:</b>\n✅ Free Delivery on All Orders\n✅ Prime Music & Video\n✅ Exclusive Member Deals\n\n👉 <b>Join Now (Free Trial):</b> {link}"
        },
        {
            "name": "Amazon Business (GST Invoice)",
            "url": f"https://www.amazon.in/tryab?tag={aff_id}",
            "desc": "💼 <b>Save 28% Extra with GST Invoice!</b>\n\nRegister your Business Account for FREE and get exclusive business pricing and GST claims on every purchase.\n\n✨ <b>Best for Resellers & Shop Owners!</b>\n👉 <b>Register Free Account:</b> {link}"
        },
        {
            "name": "Audible 90-Days Free",
            "url": f"https://www.amazon.in/dp/B077S5CVYQ?tag={aff_id}",
            "desc": "🎧 <b>Listen to 100,000+ Audiobooks for FREE!</b>\n\nGet 90 days of Audible membership for absolutely zero cost. Perfect for learning and entertainment.\n\n👉 <b>Claim 90-Day Free Trial:</b> {link}"
        }
    ]
    selected = random.choice(bounties)
    return selected["desc"].format(link=selected["url"])

# ---------- Short Link Helper ----------
async def get_short_url(target_url: str) -> str:
    """Return a cached short URL or generate a new one via CLICK_TRACKER.
    If CLICK_TRACKER is not configured or the URL is an Amazon link, return the original.
    """
    if not CLICK_TRACKER_URL or "amazon." in target_url:
        return target_url
    if not await is_url_accessible(target_url):
        print(f"[WARN] Target URL unreachable, using original: {target_url}")
        return target_url
    cache_file = "short_links_cache.json"
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
        except Exception:
            pass
    if target_url in cache:
        return cache[target_url]
    api_url = f"{CLICK_TRACKER_FUNC}?action=shorten&url={quote(target_url)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BudgetDealsBot/1.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(api_url, timeout=15) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    short_url = data.get("shortUrl")
                    if short_url:
                        cache[target_url] = short_url
                        with open(cache_file, "w") as f:
                            json.dump(cache, f)
                        return short_url
                except Exception as json_e:
                    text = await response.text()
                    print(f"JSON Parse Error: {json_e} | Response: {text[:100]}")
            else:
                text = await response.text()
                print(f"API Error: {response.status} | Response: {text[:100]}")
    return f"{CLICK_TRACKER_FUNC}?url={quote(target_url)}"

import referral_manager

# ---------- Referral Integration ----------
async def broadcast_referral(bot, chat_id, admin_user_id):
    try:
        link = referral_manager.generate_referral_link(admin_user_id)
        msg = f"Join the channel using my referral link and earn rewards!\n{link}"
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
    except Exception as e:
        print(f"Failed to broadcast referral: {e}")

# ---------- Main Posting Logic ----------
async def post_deals():
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    async with Bot(token=BOT_TOKEN) as bot:
        await bot.initialize()
        products = load_products()
        if not products:
            print("No products to post. Checking for Bounty...")
            bounty_msg = generate_bounty_message()
            await bot.send_message(chat_id=chat_id, text=bounty_msg, parse_mode='HTML')
            await bot.shutdown()
            return
        try:
            # Duplicate shield
            POSTED_LOG = "posted_products.json"
            posted_history = {}
            if os.path.exists(POSTED_LOG):
                try:
                    with open(POSTED_LOG, "r") as f:
                        posted_history = json.load(f)
                except: pass
            # Convert old format
            for key in list(posted_history.keys()):
                if isinstance(posted_history[key], str):
                    posted_history[key] = {"last_posted": posted_history[key], "count": 1}
            now = datetime.now()
            now_str = now.isoformat()
            eligible = []
            for p in products:
                name = p.get('name')
                if not name:
                    continue
                if name not in posted_history:
                    eligible.append(p)
                else:
                    history = posted_history[name]
                    dynamic_gap = random.randint(DYNAMIC_GAP_MIN, DYNAMIC_GAP_MAX)
                    gap_time = (now - timedelta(hours=dynamic_gap)).isoformat()
                    if history.get("count", 0) < 3 and history.get("last_posted", "") < gap_time:
                        if history.get("count", 0) == 2 and random.random() < 0.2:
                            continue
                        eligible.append(p)
            if not eligible:
                print("All products posted recently or maxed out. Skipping.")
                await bot.shutdown()
                return
            # Mode selection
            import sys
            random_mode = len(sys.argv) > 1 and sys.argv[1] == "--random"
            if random_mode:
                num_to_post = min(2, len(eligible))
                products_to_post = random.sample(eligible, num_to_post)
                print(f"Random mode: Selected {num_to_post} products.")
            else:
                num_to_post = 1  # limited to one product for testing
                products_to_post = eligible[:num_to_post]
                print(f"Normal mode: Selected {num_to_post} products.")
            # Update history
            for p in products_to_post:
                name = p.get('name')
                if name in posted_history:
                    posted_history[name]["last_posted"] = now_str
                    posted_history[name]["count"] = posted_history[name].get("count", 0) + 1
                else:
                    posted_history[name] = {"last_posted": now_str, "count": 1}
            with open(POSTED_LOG, "w") as f:
                json.dump(posted_history, f)
            current_count = increment_post_count()
            # Poll triggering
            if current_count % 15 == 0:
                await send_automated_poll(bot, chat_id)
            # Viral/Authority/Bounty interval
            viral_interval = random.randint(10, 15)
            if current_count >= viral_interval:
                print(f"Post count: {current_count}. Triggering Growth/Authority Cycle!")
                rand_val = random.random()
                if rand_val < 0.4:
                    growth_msg = generate_authority_post()
                elif rand_val < 0.7:
                    growth_msg = generate_viral_message()
                else:
                    growth_msg = generate_bounty_message()
                try:
                    await bot.send_message(chat_id=chat_id, text=growth_msg, parse_mode='HTML', disable_web_page_preview=True)
                    reset_post_count()
                except Exception as growth_e:
                    print(f"Failed to post growth hook: {growth_e}")
            # Determine cheapest product for lightning deal
            cheapest_product = None
            if products_to_post:
                cheapest_product = min(products_to_post, key=lambda p: get_price_value(p.get('price', '999999')))
            # VIP channel handling
            if VIP_CHANNEL_ID:
                vip_chat = f"@{VIP_CHANNEL_ID}" if not VIP_CHANNEL_ID.startswith("@") else VIP_CHANNEL_ID
                for vip_product in products_to_post[:2]:
                    # Reuse existing posting logic for VIP (simplified version)
                    name = vip_product.get('name', 'Product')
                    msg = generate_message(vip_product, post_count=current_count)
                    link = vip_product.get('link', '#')
                    # Validate link
                    if not await is_url_accessible(link):
                        with open('skipped_invalid_links.log', 'a', encoding='utf-8') as log_f:
                            log_f.write(f"{datetime.now().isoformat()} - Skipped VIP product with unreachable link: {link}\n")
                        continue
                    short_link = await get_short_url(link)
                    reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 BUY NOW (Amazon)", url=short_link)],
                        [InlineKeyboardButton("🔥 Share with Friends", url=f"https://t.me/share/url?url=https://t.me/{CHANNEL_ID.replace('@', '')}&text=Check%20this%20deal"),
                         InlineKeyboardButton("💰 Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]
                    ])
                    try:
                        await bot.send_message(chat_id=vip_chat, text=msg, parse_mode='HTML', reply_markup=reply_markup)
                    except Exception as e:
                        print(f"Failed VIP post for {name}: {e}")
            # Main channel posting
            posted = 0
            for product in products_to_post:
                product_name = product.get('name', 'Product').encode('ascii', 'ignore').decode('ascii')
                is_lightning = (product == cheapest_product)
                raw_link = product.get('link', '#')
                if not await is_url_accessible(raw_link):
                    with open('skipped_invalid_links.log', 'a', encoding='utf-8') as log_f:
                        log_f.write(f"{datetime.now().isoformat()} - Skipped product with unreachable link: {raw_link}\n")
                    continue
                link = await get_short_url(raw_link)
                if not await is_url_accessible(link):
                    print(f"[WARN] Shortened link unreachable, using original: {raw_link}")
                    link = raw_link
                image_url = product.get('image')
                msg = generate_message(product, post_count=current_count)
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 BUY NOW (Amazon)", url=link)],
                    [InlineKeyboardButton("🔥 Share with Friends", url=f"https://t.me/share/url?url=https://t.me/{CHANNEL_ID.replace('@', '')}&text=Check%20this%20deal"),
                     InlineKeyboardButton("💰 Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")]
                ])
                try:
                    if image_url:
                        local_image = await download_image(image_url)
                        if local_image:
                            async with aiofiles.open(local_image, 'rb') as photo_file:
                                sent_msg = await bot.send_photo(chat_id=chat_id, photo=await photo_file.read(), caption=msg, parse_mode='HTML', reply_markup=reply_markup)
                            os.remove(local_image)
                        else:
                            print(f"[WARN] Could not download image for {product_name}, falling back to text post.")
                            sent_msg = await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=reply_markup)
                    else:
                        sent_msg = await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=reply_markup)
                    posted += 1
                    print(f"Posted: {product_name}")
                    if is_lightning:
                        try:
                            await bot.pin_chat_message(chat_id=chat_id, message_id=sent_msg.message_id, disable_notification=False)
                            print(f"Pinned lightning deal: {product_name}")
                        except Exception as pin_err:
                            print(f"Could not pin message: {str(pin_err)}")
                    await asyncio.sleep(5)
                except Exception as e:
                    err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
                    print(f"Failed to post {product_name}: {err_msg}")
            # Summary message removed as requested.
            # Broadcast referral invitation
            admin_user_id = int(os.getenv('BOT_ADMIN_ID', '0'))
            if admin_user_id:
                await broadcast_referral(bot, chat_id, admin_user_id)
            await bot.shutdown()
        except Exception as e:
            err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"Error in posting: {err_msg}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Run post_deals once and exit')
    args = parser.parse_args()

    async def _run():
        if args.dry_run:
            await post_deals()
        else:
            while True:
                await post_deals()
                await asyncio.sleep(POST_INTERVAL_MINUTES * 60)

    asyncio.run(_run())
