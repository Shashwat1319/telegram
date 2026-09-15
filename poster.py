import os
import sys
import random
import re
import asyncio
import logging
import html
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
if not BOT_TOKEN:
    log.error("BOT_TOKEN environment variable is required for poster")
    sys.exit(1)
config = load_config()
bot_cfg = config.get("bot", {})
content_cfg = config.get("content", {})

CHANNEL_ID = bot_cfg.get("channel_id", os.getenv("CHANNEL_ID", "@channel"))
CHAT_ID_INPUT = CHANNEL_ID
CLEAN_ID = CHANNEL_ID.replace("@", "") if CHANNEL_ID else "channel"
SOURCE_FILE = content_cfg.get("source_file", "content.json")
POSTS_PER_BATCH = content_cfg.get("posts_per_batch", 3)
MAX_REPOSTS = content_cfg.get("max_reposts", 10)
HAS_LINKS = content_cfg.get("has_links", True)
LINK_TRACKING = content_cfg.get("link_tracking_enabled", False)
PIN_POSTS = content_cfg.get("pin_posts", False)
HASHTAGS = " ".join(content_cfg.get("hashtags", ["#AmazonDeals", "#LootOffer", "#PriceDrop"]))
DAILY_POLL = content_cfg.get("daily_poll", True)
POST_TO_PREMIUM = content_cfg.get("post_to_premium", False)
PREMIUM_CHANNEL_ID = content_cfg.get("premium_channel_id", bot_cfg.get("premium_channel_handle", "@smartgahrpremium"))
COUNTER_FILE = "post_count.txt"

CTA_OPTIONS = [
    "💬 Isse sasta kahin mila? Comment karo 👇",
    "🗳️ Aaj ki deal kaunsi best lagi? Reply me batao!",
    "📝 Is product ki review chahiye? Comment me bolo — hum test karke batayenge",
    "🔄 Apne group me share karo — sabko bachao paise!",
    "👍 Deal achhi lagi? Reaction do — kal aur aisi hi deal aayegi",
    "❓ Is price pe khareedna chahiye ya wait karein? Comment karo",
    "🏷️ Kisi aur cheez ka deal chahiye? Comment me batao — dhundh ke layenge!",
    "🔥 Ye deal 24 ghante mein expire ho sakti hai — jaldi karo!",
    "📦 Maine khud ye order kiya hai — quality guaranteed! 💯",
    "🎯 Budget under ₹999 me aur kya chahiye? Comment karo!",
]


def _posted_path():
    return SOURCE_FILE.replace(".json", "_posted.json")


def _load_posted():
    return load_json(_posted_path(), default={})


def _save_posted(data):
    save_json(_posted_path(), data)


def _pick_eligible(items, posted):
    now = datetime.now()
    unposted = []
    repostable = []
    for item in items:
        item_id = item.get("id") or item.get("title")
        if not item_id:
            continue
        if item_id not in posted:
            unposted.append(item)
        else:
            h = posted[item_id]
            if item.get("format") in ("trust_check", "amazon_verified"):
                gap = random.randint(2, 4)
            else:
                gap = random.randint(8, 16)
            if h.get("count", 0) < MAX_REPOSTS and h.get("last", "") < (now - timedelta(hours=gap)).isoformat():
                repostable.append(item)
    if unposted:
        random.shuffle(unposted)
        return unposted
    repostable.sort(key=lambda i: posted.get(i.get("id") or i.get("title"), {}).get("last", ""))
    if len(repostable) > 3:
        top = repostable[:3]
        rest = repostable[3:]
        random.shuffle(rest)
        repostable = top + rest
    return repostable


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
    tmp = COUNTER_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write(str(c))
    os.replace(tmp, COUNTER_FILE)
    return c


def _safe_truncate(text, max_len):
    """Truncate text without breaking HTML tags."""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    # Count unclosed tags
    opens = len(re.findall(r'<[bius]>', cut))
    closes = len(re.findall(r'</[bius]>', cut))
    while opens > closes and cut:
        cut = cut[:cut.rfind('<')]
        opens = len(re.findall(r'<[bius]>', cut))
        closes = len(re.findall(r'</[bius]>', cut))
    return cut + "..."


def generate_high_converting_message(item, post_count=0):
    """Generates high-converting copywriting templates for affiliate posts."""
    title = str(item.get("title", "Amazon Deal"))[:60]
    price = str(item.get("price", ""))
    mrp = str(item.get("mrp", ""))
    disc = str(item.get("discount", ""))
    rating = str(item.get("rating", "4.5★"))
    is_loot = item.get("is_loot", False)
    body = str(item.get("body", ""))[:400]

    badge = "🚨 <b>BIGGEST PRICE DROP LOOT</b>" if is_loot else "⚡ <b>VERIFIED AMAZON DEAL</b>"
    
    urgency_options = [
        "⏰ <i>Offer active while Amazon stocks last!</i>",
        "🔥 <i>Lightning Deal — Price may rise anytime!</i>",
        "📉 <i>Lowest price recorded recently. Don't wait!</i>",
        "🎯 <i>High demand item — Grab before sold out!</i>",
    ]

    if body:
        body_html = body.replace("\n\n", "\n")
        body_html = re.sub(r"~~(.+?)~~", r"<s>\1</s>", body_html)
        body_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body_html)
        body_html = re.sub(r"__(.+?)__", r"<i>\1</i>", body_html)
        body_html = html.escape(body_html, quote=False)
        body_html = re.sub(r'<s>(.+?)</s>', r'<s>\1</s>', body_html)
        body_html = re.sub(r'<b>(.+?)</b>', r'<b>\1</b>', body_html)
        body_html = re.sub(r'<i>(.+?)</i>', r'<i>\1</i>', body_html)
        msg = f"{badge}\n\n📦 <b>{html.escape(title)}</b>\n\n{body_html}\n\n{random.choice(urgency_options)}"
    else:
        hook = item.get("hook", "Grab this deal before price goes up!")
        price_line = ""
        if price and mrp:
            price_line = f"💰 <b>Price</b>: <s>{html.escape(mrp)}</s> → <b>{html.escape(price)}</b> ({html.escape(disc)} OFF)"
        elif price:
            price_line = f"💰 <b>Deal Price</b>: <b>{html.escape(price)}</b>"
        templates = [
            f"{badge}\n\n📦 <b>{html.escape(title)}</b>\n\n{price_line}\n⭐ <b>Rating</b>: {html.escape(rating)}\n\n🔥 <i>{html.escape(hook)}</i>\n\n{random.choice(urgency_options)}",
            f"🔥 <b>LOOT ALERT ({html.escape(disc)} OFF)</b>\n\n📦 <b>{html.escape(title)}</b>\n\n{price_line}\n\n✅ Verified Amazon India Deal\n{random.choice(urgency_options)}",
            f"⚡ <b>FLASH SALE ITEM</b>\n\n📦 <b>{html.escape(title)}</b>\n\n{price_line}\n⭐ <b>User Rating</b>: {html.escape(rating)}\n\n{random.choice(urgency_options)}",
        ]
        msg = templates[post_count % len(templates)]

    msg += f"\n\n📢 <b>Join</b> @{html.escape(CLEAN_ID)} for daily loots!"
    if HASHTAGS:
        msg += f"\n{HASHTAGS}"
    msg += f"\n\n{random.choice(CTA_OPTIONS)}"
    return msg


async def post_content():
    if CHAT_ID_INPUT.startswith("@") or CHAT_ID_INPUT.lstrip("-").isdigit():
        chat_id = CHAT_ID_INPUT
    else:
        chat_id = f"@{CHAT_ID_INPUT}"
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            items = load_content_items(SOURCE_FILE)
            if not items:
                log.info("No items available to post.")
                return

            posted = _load_posted()
            eligible = _pick_eligible(items, posted)
            if not eligible:
                log.info("All items posted recently. Skipping cycle.")
                return

            num = min(POSTS_PER_BATCH, len(eligible))
            to_post = eligible[:num]
            
            current_count = _increment_post_count()
            posted_now = []
            for item in to_post:
                title = item.get("title", "Deal")
                raw_link = item.get("link", "") if HAS_LINKS else ""
                product_id = item.get("product_id", "")
                link = tracked_url(raw_link, product_id, title=item.get("title"), price=item.get("price"), discount=item.get("discount"), image=item.get("image")) if raw_link and LINK_TRACKING else raw_link
                msg = generate_high_converting_message(item, current_count)
                if link:
                    msg = f'<a href="{link}">&#8203;</a>{msg}'

                buttons = []
                if link:
                    btn_label = f"🛒 BUY ON AMAZON ({item.get('discount', 'DEAL')})" if item.get('discount') else "🛒 BUY NOW ON AMAZON ⚡"
                    buttons.append([InlineKeyboardButton(btn_label, url=link)])
                
                buttons.append([
                    InlineKeyboardButton("🚀 Share Deal", url=f"https://t.me/share/url?url={quote(link or 'https://t.me/' + CLEAN_ID)}&text={quote(title[:60])}"),
                ])
                buttons.append([
                    InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CLEAN_ID}"),
                    InlineKeyboardButton("🔥 More Deals", url=f"https://t.me/{CLEAN_ID}"),
                ])
                
                kb = InlineKeyboardMarkup(buttons)
                success = False
                for attempt in range(3):
                    try:
                        if len(msg) > 4000:
                            msg = _safe_truncate(msg, 3950) + "\n\n⚠️ Truncated. Join channel for full details."
                        sent = await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=kb)
                        log.info("Posted deal to channel: %s", title[:40])
                        if PIN_POSTS:
                            try:
                                await bot.pin_chat_message(chat_id=chat_id, message_id=sent.message_id)
                            except TelegramError:
                                pass
                        success = True
                        break
                    except TelegramError as e:
                        if attempt < 2:
                            wait = (attempt + 1) * 5
                            log.warning("Telegram error for %s (attempt %d/3): %s — retrying in %ds", title[:30], attempt + 1, e, wait)
                            await asyncio.sleep(wait)
                        else:
                            log.error("Failed to post %s after 3 attempts: %s", title[:30], e)
                    except Exception as e:
                        log.error("Failed to post %s: %s", title[:30], e)
                        break

                if success:
                    item_id = item.get("id") or item.get("title", "")
                    posted[item_id] = {
                        "last": datetime.now().isoformat(),
                        "count": posted.get(item_id, {}).get("count", 0) + 1 if item_id in posted else 1
                    }
                    posted_now.append(item)
                    post_delay = content_cfg.get("post_delay_seconds", 3)
                    await asyncio.sleep(post_delay)

            if posted_now:
                _save_posted(posted)

            if POST_TO_PREMIUM and posted_now:
                premium_item = to_post[0]
                try:
                    p_title = html.escape(str(premium_item.get('title', 'Deal')))
                    p_body = html.escape(str(premium_item.get('body', '')))[:300]
                    p_link = premium_item.get('link', '')
                    p_tracked = tracked_url(p_link, premium_item.get("product_id"), title=premium_item.get("title"), price=premium_item.get("price"), discount=premium_item.get("discount"), image=premium_item.get("image")) if p_link and LINK_TRACKING else p_link
                    premium_msg = f'🔒 <b>PREMIUM EXCLUSIVE</b>\n\n📦 <b>{p_title}</b>\n\n{p_body}\n\n🔗 <a href="{p_tracked}">🛒 Buy on Amazon</a>'
                    if len(premium_msg) > 4000:
                        premium_msg = _safe_truncate(premium_msg, 3950) + "\n\n⚠️ Truncated."
                    await bot.send_message(
                        chat_id=PREMIUM_CHANNEL_ID,
                        text=premium_msg,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🛒 BUY NOW", url=tracked_url(premium_item.get("link", ""), premium_item.get("product_id")) if premium_item.get("link") and LINK_TRACKING else premium_item.get("link", "")),
                        ]]),
                    )
                    log.info("Posted premium deal to %s", PREMIUM_CHANNEL_ID)
                except Exception as e:
                    log.error("Premium posting failed: %s", e)

            if DAILY_POLL:
                try:
                    await post_daily_poll(bot, chat_id, items, posted)
                except Exception as e:
                    log.error("Poll posting failed: %s", e)

    except Exception as e:
        log.error("post_content fatal error: %s", e)


async def post_daily_poll(bot, chat_id, items, posted):
    """Posts a daily engagement poll with the last few posted deals as options."""
    if not items:
        return
    recent = []
    for item in items:
        item_id = item.get("id") or item.get("title", "")
        h = posted.get(item_id)
        if h and item_id in posted:
            recent.append((h.get("last", ""), item))
    recent.sort(key=lambda x: x[0], reverse=True)
    recent = [item for _, item in recent[:4]]
    if len(recent) < 2:
        recent = items[:min(4, len(items))]
    options = []
    for item in recent:
        price = item.get("price", "")
        title = item.get("title", "Deal")
        short = title[:60]
        if len(short) > 58:
            short = short[:57] + "…"
        options.append(f"{short}")
    while len(options) > 4:
        options.pop()
    if len(options) < 2:
        log.info("Not enough options for poll, skipping")
        return
    question = "🔥 Aaj ki best deal kaunsi lagi?"
    try:
        await bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options[:4],
            is_anonymous=False,
            allows_multiple_answers=False,
        )
        log.info("Daily poll posted with %d options", len(options))
    except TelegramError as e:
        log.error("Poll send error: %s", e)


def post_next_deal():
    asyncio.run(post_content())


if __name__ == "__main__":
    post_next_deal()
