import os
import random
import re
import asyncio
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config_loader import load_config
from utils import tracked_url, load_content_items
from data import load_json, save_json

load_dotenv()
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
config = load_config()
bot_cfg = config.get("bot", {})
content_cfg = config.get("content", {})

CHANNEL_ID = bot_cfg.get("channel_id", os.getenv("CHANNEL_ID", "@channel"))
CHAT_ID_INPUT = CHANNEL_ID
CLEAN_ID = CHANNEL_ID.replace("@", "") if CHANNEL_ID else "channel"
SOURCE_FILE = content_cfg.get("source_file", "content.json")
POSTS_PER_BATCH = content_cfg.get("posts_per_batch", 3)
MAX_REPOSTS = content_cfg.get("max_reposts", 50)
HAS_LINKS = content_cfg.get("has_links", True)
LINK_TRACKING = content_cfg.get("link_tracking_enabled", False)
PIN_POSTS = content_cfg.get("pin_posts", False)
HASHTAGS = " ".join(content_cfg.get("hashtags", ["#AmazonDeals", "#LootOffer", "#PriceDrop"]))
COUNTER_FILE = "post_count.txt"


def _posted_path():
    return SOURCE_FILE.replace(".json", "_posted.json")


def _load_posted():
    return load_json(_posted_path(), default={})


def _save_posted(data):
    save_json(_posted_path(), data)


def _pick_eligible(items, posted):
    now = datetime.now()
    eligible = []
    for item in items:
        item_id = item.get("id") or item.get("title")
        if not item_id:
            continue
        if item_id not in posted:
            eligible.append(item)
        else:
            h = posted[item_id]
            gap = random.randint(8, 16)
            if h.get("count", 0) < MAX_REPOSTS and h.get("last", "") < (now - timedelta(hours=gap)).isoformat():
                eligible.append(item)
    return eligible


def _get_post_count():
    if not os.path.exists(COUNTER_FILE):
        return 0
    try:
        with open(COUNTER_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def _increment_post_count():
    c = _get_post_count() + 1
    with open(COUNTER_FILE, "w") as f:
        f.write(str(c))
    return c


def generate_high_converting_message(item, post_count=0):
    """Generates high-converting copywriting templates for affiliate posts."""
    title = item.get("title", "Amazon Deal")
    price = item.get("price", "")
    mrp = item.get("mrp", "")
    disc = item.get("discount", "")
    rating = item.get("rating", "4.5★")
    is_loot = item.get("is_loot", False)
    body = item.get("body", "")

    badge = "🚨 <b>BIGGEST PRICE DROP LOOT</b>" if is_loot else "⚡ <b>VERIFIED AMAZON DEAL</b>"
    
    urgency_options = [
        "⏰ <i>Offer active while Amazon stocks last!</i>",
        "🔥 <i>Lightning Deal — Price may rise anytime!</i>",
        "📉 <i>Lowest price recorded recently. Don't wait!</i>",
        "🎯 <i>High demand item — Grab before sold out!</i>",
    ]

    if body:
        body_html = body.replace("\n\n", "\n")
        body_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body_html)
        body_html = re.sub(r"__(.+?)__", r"<i>\1</i>", body_html)
        msg = f"{badge}\n\n📦 <b>{title}</b>\n\n{body_html}\n\n{random.choice(urgency_options)}"
    else:
        hook = item.get("hook", "Grab this deal before price goes up!")
        price_line = ""
        if price and mrp:
            price_line = f"💰 <b>Price</b>: <s>{mrp}</s> → <b>{price}</b> ({disc} OFF)"
        elif price:
            price_line = f"💰 <b>Deal Price</b>: <b>{price}</b>"
        templates = [
            f"{badge}\n\n📦 <b>{title}</b>\n\n{price_line}\n⭐ <b>Rating</b>: {rating}\n\n🔥 <i>{hook}</i>\n\n{random.choice(urgency_options)}",
            f"🔥 <b>LOOT ALERT ({disc} OFF)</b>\n\n📦 <b>{title}</b>\n\n{price_line}\n\n✅ Verified Amazon India Deal\n{random.choice(urgency_options)}",
            f"⚡ <b>FLASH SALE ITEM</b>\n\n📦 <b>{title}</b>\n\n{price_line}\n⭐ <b>User Rating</b>: {rating}\n\n{random.choice(urgency_options)}",
        ]
        msg = templates[post_count % len(templates)]

    msg += f"\n\n📢 <b>Join</b> @{CLEAN_ID} for daily loots!"
    if HASHTAGS:
        msg += f"\n{HASHTAGS}"
    return msg


async def post_content():
    if CHAT_ID_INPUT.startswith("@") or CHAT_ID_INPUT.lstrip("-").isdigit():
        chat_id = CHAT_ID_INPUT
    else:
        chat_id = f"@{CHAT_ID_INPUT}"
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            await bot.initialize()
            items = load_content_items(SOURCE_FILE)
            if not items:
                log.info("No items available to post.")
                await bot.shutdown()
                return

            posted = _load_posted()
            eligible = _pick_eligible(items, posted)
            if not eligible:
                log.info("All items posted recently. Skipping cycle.")
                await bot.shutdown()
                return

            num = min(POSTS_PER_BATCH, len(eligible))
            to_post = eligible[:num]  # Picks highest discount eligible items first
            
            now_str = datetime.now().isoformat()
            for item in to_post:
                item_id = item.get("id") or item.get("title", "")
                posted[item_id] = {
                    "last": now_str,
                    "count": posted.get(item_id, {}).get("count", 0) + 1 if item_id in posted else 1
                }
            _save_posted(posted)

            current_count = _increment_post_count()
            for item in to_post:
                title = item.get("title", "Deal")
                raw_link = item.get("link", "") if HAS_LINKS else ""
                product_id = item.get("product_id", "")
                link = tracked_url(raw_link, product_id, title=item.get("title"), price=item.get("price"), discount=item.get("discount"), image=item.get("image")) if raw_link and LINK_TRACKING else raw_link
                msg = generate_high_converting_message(item, current_count)

                buttons = []
                if link:
                    btn_label = f"🛒 BUY ON AMAZON ({item.get('discount', 'DEAL')})" if item.get('discount') else "🛒 BUY NOW ON AMAZON ⚡"
                    buttons.append([InlineKeyboardButton(btn_label, url=link)])
                
                buttons.append([
                    InlineKeyboardButton("🚀 Share Deal", url=f"https://t.me/share/url?url={quote(link or 'https://t.me/' + CLEAN_ID)}&text={quote(title[:60])}"),
                    InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CLEAN_ID}")
                ])
                
                kb = InlineKeyboardMarkup(buttons)
                try:
                    sent = await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=kb)
                    log.info("Posted deal to channel: %s", title[:40])
                    if PIN_POSTS:
                        try:
                            await bot.pin_chat_message(chat_id=chat_id, message_id=sent.message_id)
                        except TelegramError:
                            pass
                    await asyncio.sleep(3)
                except TelegramError as e:
                    log.error("Telegram posting error for %s: %s", title, e)
                except Exception as e:
                    log.error("Failed to post %s: %s", title, e)

            await bot.shutdown()
    except Exception as e:
        log.error("post_content fatal error: %s", e)


def post_next_deal():
    asyncio.run(post_content())


if __name__ == "__main__":
    post_next_deal()
