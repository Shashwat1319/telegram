# -*- coding: utf-8 -*-
import json, time, random, asyncio, os, sys, re, aiohttp, aiofiles, hashlib, logging
from urllib.parse import quote
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from functools import lru_cache

from utils import get_price_value, format_price, calc_discount

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CLEAN_ID = CHANNEL_ID.replace('@', '') if CHANNEL_ID else "channel"
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "")
CLICK_TRACKER_FUNC = f"{CLICK_TRACKER_URL}/.netlify/functions/go" if CLICK_TRACKER_URL else ""
POST_INTERVAL_MINUTES = int(os.getenv("POST_INTERVAL_MINUTES", "30"))
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID")
POSTED_LOG = "posted_products.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

async def is_url_accessible(url):
    if "amazon." in url: return True
    try:
        async with aiohttp.ClientSession() as s:
            async with s.head(url, timeout=5) as r:
                return r.status < 400
    except: return False

async def download_image(url):
    if not url: return None
    if not await is_url_accessible(url): return None
    cache_dir = os.path.join(os.getcwd(), "image_cache")
    os.makedirs(cache_dir, exist_ok=True)
    filename = hashlib.sha1(url.encode()).hexdigest() + ".jpg"
    local = os.path.join(cache_dir, filename)
    if os.path.exists(local): return local
    headers = {"User-Agent": "Mozilla/5.0 Windows Chrome/120"}
    async with aiohttp.ClientSession(headers=headers) as s:
        try:
            async with s.get(url, timeout=15) as r:
                if r.status == 200:
                    with open(local, 'wb') as f:
                        async for chunk in r.content.iter_chunked(8192): f.write(chunk)
                    return local
        except: pass
    return None

COUNTER_FILE = "post_count.txt"
def get_post_count():
    if os.path.exists(COUNTER_FILE):
        try: return int(open(COUNTER_FILE).read().strip())
        except: return 0
    return 0
def increment_post_count():
    c = get_post_count() + 1
    open(COUNTER_FILE, "w").write(str(c))
    return c

def load_products():
    return json.load(open("product.json", encoding="utf-8"))["products"]

def generate_message(product, post_count=0):
    name = product.get('name', 'Deal!')
    price = format_price(product.get('price', 'Check'))

    hook = product.get('hook', 'Bhai ye loot miss mat karna!')
    pain = product.get('pain', '')
    fix = product.get('fix', 'Solid deal hai abhi order karo.')
    loot_reason = product.get('loot_reason', '')
    rating = product.get('rating', '')
    drop = calc_discount(product.get('price', '0'), product.get('mrp', '0'))

    badge = f"🔥 PRICE DROP: {drop}% OFF" if drop >= 30 else (f"📉 PRICE DROP: {drop}%" if drop > 0 else "⚡ HOT DEAL")
    templates = [
        f"🔥 <b>{badge}</b> 🔥\n\n<b>{name[:60]}</b>\n\n💸 <b>Price:</b> <s>{product.get('mrp', '')}</s> → <b>{price}</b>\n✅ {fix}\n⏰ Limited stock — price can go up anytime!",
        f"😤 {pain}\n\n✅ <b>Solution:</b> {name[:50]}\n💸 <b>Price:</b> {price}\n✔️ {fix}\n⏰ Grab it before price hikes!",
        f"⭐ <b>Today's Best Deal</b>\n\n📦 <b>{name[:55]}</b>\n💸 <b>Price:</b> {price} (Save {drop}%)\n✔️ {fix}\n📉 {loot_reason}\n⏰ Limited time!",
    ]
    msg = templates[post_count % len(templates)]
    if rating and rating != "Not specified":
        msg += f"\n⭐ Rating: {rating}"
    current_time = datetime.now().strftime('%I:%M %p')
    msg += f"\n\n✅ Verified at {current_time} IST\n📢 Join @{CLEAN_ID} for daily deals!"
    msg += "\n\n<tg-spoiler>🏷️ #LootDeals #AmazonSale #BudgetFinds #DealsIndia</tg-spoiler>"
    return msg

async def get_short_url(target_url):
    if not CLICK_TRACKER_URL: return target_url
    cache_file = "short_links_cache.json"
    cache = {}
    if os.path.exists(cache_file):
        try: cache = json.load(open(cache_file))
        except: pass
    if target_url in cache: return cache[target_url]
    api = f"{CLICK_TRACKER_FUNC}?action=shorten&url={quote(target_url)}"
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(api, timeout=15) as r:
                if r.status == 200:
                    data = await r.json()
                    su = data.get("shortUrl")
                    if su:
                        cache[target_url] = su
                        json.dump(cache, open(cache_file, "w"))
                        return su
        except: pass
    return f"{CLICK_TRACKER_FUNC}?url={quote(target_url)}"

async def post_deals():
    chat_id = f"@{CHANNEL_ID}" if not CHANNEL_ID.startswith("@") else CHANNEL_ID
    async with Bot(token=BOT_TOKEN) as bot:
        await bot.initialize()
        products = load_products()
        if not products:
            log.info("No products to post.")
            await bot.shutdown()
            return

        posted = {}
        if os.path.exists(POSTED_LOG):
            try: posted = json.load(open(POSTED_LOG))
            except: pass
        for k in list(posted.keys()):
            if isinstance(posted[k], str): posted[k] = {"last": posted[k], "count": 1}

        now = datetime.now()
        now_str = now.isoformat()
        eligible = []
        for p in products:
            name = p.get('name')
            if not name: continue
            if name not in posted:
                eligible.append(p)
            else:
                h = posted[name]
                gap = random.randint(12, 24)
                if h.get("count", 0) < 3 and h.get("last", "") < (now - timedelta(hours=gap)).isoformat():
                    eligible.append(p)
        if not eligible:
            log.info("All products posted recently. Skipping.")
            await bot.shutdown()
            return

        random_mode = "--random" in sys.argv
        num = min(3, len(eligible))
        to_post = random.sample(eligible, num) if random_mode else eligible[:num]
        log.info("Posting %d products.", len(to_post))

        for p in to_post:
            posted[p['name']] = {"last": now_str, "count": posted.get(p['name'], {}).get("count", 0) + 1 if p['name'] in posted else 1}
        json.dump(posted, open(POSTED_LOG, "w"))

        current_count = increment_post_count()
        cheapest = min(to_post, key=lambda p: get_price_value(p.get('price', '999999')))

        for product in to_post:
            name = product.get('name', 'Product')
            raw_link = product.get('link', '#')
            if not await is_url_accessible(raw_link): continue
            link = await get_short_url(raw_link)
            image_url = product.get('image')
            msg = generate_message(product, current_count)
            is_cheapest = (product == cheapest)

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 BUY NOW (Amazon)", url=link)],
                [InlineKeyboardButton("🔥 Share", url=f"https://t.me/share/url?url=https://t.me/{CLEAN_ID}&text=Check%20this%20deal%20{quote(name[:50])}"),
                 InlineKeyboardButton("💰 Join", url=f"https://t.me/{CLEAN_ID}")]
            ])

            try:
                if image_url:
                    local = await download_image(image_url)
                    if local:
                        async with aiofiles.open(local, 'rb') as f:
                            sent = await bot.send_photo(chat_id=chat_id, photo=await f.read(), caption=msg, parse_mode='HTML', reply_markup=kb)
                        os.remove(local)
                    else:
                        sent = await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=kb)
                else:
                    sent = await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=kb)

                if is_cheapest:
                    try: await bot.pin_chat_message(chat_id=chat_id, message_id=sent.message_id)
                    except: pass
                await asyncio.sleep(5)
            except Exception as e:
                log.error("Failed to post %s: %s", name, e)

        await bot.shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--random', action='store_true')
    args = parser.parse_args()

    async def _run():
        if args.dry_run:
            await post_deals()
        else:
            while True:
                await post_deals()
                await asyncio.sleep(POST_INTERVAL_MINUTES * 60)

    asyncio.run(_run())
