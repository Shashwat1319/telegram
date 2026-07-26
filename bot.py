import os, random, logging, asyncio, argparse, time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config_loader import load_config
from utils import esc_md, tracked_url, load_content_items
from data import load_json

load_dotenv()
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")
config = load_config()
bot_cfg = config.get("bot", {})
BOT_USERNAME = bot_cfg.get("username", os.getenv("BOT_USERNAME", "YourBot"))
CHANNEL_ID = bot_cfg.get("channel_id", os.getenv("CHANNEL_ID", "@channel"))
CHANNEL_HANDLE = bot_cfg.get("channel_handle", "channel")
WELCOME_MSG = bot_cfg.get("welcome_message", "Welcome!")
REFERRAL_REMINDER_MSG = bot_cfg.get("referral_reminder_message", "Invite friends and earn rewards!")
CONTENT_CMD = bot_cfg.get("content_command", "random")
CONTENT_CMD_LABEL = bot_cfg.get("content_command_label", "Get Content")
CONTENT_SOURCE = config.get("content", {}).get("source_file", "content.json")

_content_cache = {"items": None, "ts": 0.0}

def get_random_item():
    now = time.monotonic()
    if _content_cache["items"] is None or now - _content_cache["ts"] > 60:
        _content_cache["items"] = load_content_items(CONTENT_SOURCE)
        _content_cache["ts"] = now
    items = _content_cache["items"]
    if not items:
        return None
    posted_path = CONTENT_SOURCE.replace(".json", "_posted.json")
    posted = load_json(posted_path, default={})
    unposted = [it for it in items if (it.get("id") or it.get("title")) not in posted]
    return random.choice(unposted if unposted else items)

async def start(update, context):
    user = update.effective_user
    msg = (
        f"👋 *Welcome {user.first_name}!*\n\n{esc_md(WELCOME_MSG)}\n\n"
        f"📌 *Commands:*\n"
        f"• /{CONTENT_CMD} — {CONTENT_CMD_LABEL}\n"
        f"• /referral — Invite friends & earn rewards\n"
        f"• /topdeal — Best discount deal\n"
        f"• /search <kw> — Search deals\n\n"
        f"🎯 *Refer 5 friends → 1.5x points | Refer 10 → 2x points*\n\n"
        f"Join @{esc_md(CHANNEL_HANDLE)} for daily deals! 🚀"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_HANDLE}")],
        [InlineKeyboardButton("🎯 Get Referral Link", url=f"https://t.me/{BOT_USERNAME}?start=ref")],
        [InlineKeyboardButton(f"🔥 {CONTENT_CMD_LABEL}", callback_data=CONTENT_CMD)],
    ])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def random_item(update, context):
    item = get_random_item()
    if not item or not isinstance(item, dict):
        await update.message.reply_text("No content available right now. Check back soon!")
        return
    title = str(item.get("title", "Item"))[:60]
    body = str(item.get("body", ""))[:200]
    link = item.get("link", "")
    image = item.get("image", "")
    tracked = tracked_url(link, title=item.get("title"), price=item.get("price"), discount=item.get("discount"), image=item.get("image")) if link else ""
    msg = f"*{title}*\n\n{body}"
    if tracked:
        msg += f"\n\n👉 [Learn More]({tracked})"
    msg += f"\n\n📢 Join @{esc_md(CHANNEL_HANDLE)} for more!"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Open", url=tracked or link)],
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_HANDLE}")]
    ])
    if image:
        try:
            await update.message.reply_photo(photo=image, caption=msg, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception:
            pass
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

_referral_cooldowns = {}
_referral_cooldown_lock = asyncio.Lock()

async def referral(update, context):
    user = update.effective_user
    now = time.monotonic()
    async with _referral_cooldown_lock:
        last = _referral_cooldowns.get(user.id, 0)
        if now - last < 30:
            remaining = int(30 - (now - last))
            await update.message.reply_text(f"⏳ Please wait {remaining}s before using /referral again.")
            return
        _referral_cooldowns[user.id] = now
    try:
        from referral import generate_referral_link, get_user_stats
        link = await generate_referral_link(user.id)
        _, count, points = get_user_stats(user.id)
    except Exception as e:
        log.error("Referral error for user %d: %s", user.id, e)
        await update.message.reply_text("❌ Could not generate referral link right now. Make sure the bot is admin in the channel. Try again later.")
        return
    progress_5 = "▓" * min(count, 5) + "░" * (5 - min(count, 5))
    progress_10 = "▓" * max(0, min(count - 5, 5)) + "░" * max(0, 5 - max(0, count - 5))
    next_tier = "2x points" if count >= 10 else "1.5x points" if count >= 5 else "1.5x points (at 5)"
    msg = (
        f"🎯 *Your Referral Link*\n\n"
        f"Share this link with friends — when they join, you earn points!\n\n"
        f"🔗 `{link}`\n\n"
        f"📊 *Your Stats:*\n"
        f"• People referred: *{count}*\n"
        f"• Points earned: *{points}*\n\n"
        f"👥 *Tier Progress:*\n"
        f"  Tier 1 (5 refs): `{progress_5}` {count}/5\n"
        f"  Tier 2 (10 refs): `{progress_10}` {count}/10\n"
        f"  Current rate: {next_tier}\n\n"
        f"Keep sharing — more referrals = bigger rewards!"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}&text=Join%20%40{CHANNEL_HANDLE}%21")],
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_HANDLE}")]
    ])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def topdeal(update, context):
    items = load_content_items(CONTENT_SOURCE)
    if not items:
        await update.message.reply_text("No deals available right now.")
        return
    sorted_items = sorted(items, key=lambda x: x.get("discount_val", 0), reverse=True)
    top = sorted_items[0]
    title = top.get("title", "Deal")[:60]
    body = top.get("body", "")[:200]
    link = top.get("link", "")
    tracked = tracked_url(link, top.get("product_id"), title=top.get("title"), price=top.get("price"), discount=top.get("discount"), image=top.get("image")) if link else ""
    msg = f"🏆 *TOP DEAL TODAY*\n\n*{title}*\n\n{body}"
    if tracked:
        msg += f"\n\n👉 [Grab Deal]({tracked})"
    msg += f"\n\n📢 Join @{esc_md(CHANNEL_HANDLE)} for more!"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", url=tracked or link)],
        [InlineKeyboardButton("📢 Channel", url=f"https://t.me/{CHANNEL_HANDLE}")]
    ])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def search(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /search <keyword>\nExample: /search earbuds")
        return
    keyword = " ".join(context.args).lower()
    items = load_content_items(CONTENT_SOURCE)
    matches = [i for i in items if keyword in i.get("title", "").lower() or keyword in i.get("category", "").lower()]
    if not matches:
        await update.message.reply_text(f"❌ No deals found for '{keyword}'. Try a different keyword.")
        return
    seen = set()
    result = []
    for m in matches:
        pid = m.get("product_id", m.get("title", ""))
        if pid not in seen:
            seen.add(pid)
            disc = m.get("discount", "")
            title = m.get("title", "?")[:50]
            result.append(f"• {title} — {disc}")
            if len(result) >= 5:
                break
    msg = f"🔍 *Search Results for '{keyword}'*\n\n" + "\n".join(result)
    msg += f"\n\n📢 Join @{esc_md(CHANNEL_HANDLE)} for more!"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def about(update, context):
    desc = load_config().get("bot", {}).get("description", "A Telegram bot.")
    msg = f"ℹ️ *About This Bot*\n\n{esc_md(desc)}\n\n🤖 *Bot:* @{esc_md(BOT_USERNAME)}\n📢 *Channel:* @{esc_md(CHANNEL_HANDLE)}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def contact(update, context):
    msg = f"📬 *Contact*\n\nJoin our channel @{esc_md(CHANNEL_HANDLE)} for updates.\nUse /start to see all available commands."
    await update.message.reply_text(msg, parse_mode="Markdown")

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == CONTENT_CMD:
        item = get_random_item()
        if not item:
            await query.edit_message_text("No content available right now. Check back soon!")
            return
        title = item.get("title", "Item")
        body = item.get("body", "")
        link = item.get("link", "")
        tracked = tracked_url(link, title=item.get("title"), price=item.get("price"), discount=item.get("discount"), image=item.get("image")) if link else ""
        msg = f"*{title[:60]}*\n\n{body[:200]}"
        if tracked:
            msg += f"\n\n👉 [Learn More]({tracked})"
        msg += f"\n\n📢 Join @{esc_md(CHANNEL_HANDLE)} for more!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Open", url=tracked or link)],
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_HANDLE}")]
        ])
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)

async def error_handler(update, context):
    log.error("Update %s caused error: %s", update, context.error)

async def post_referral_reminder(bot: Bot, pin=False):
    try:
        count = await bot.get_chat_member_count(CHANNEL_ID)
    except Exception:
        count = "N/A"
    msg = (
        f"🎯 *Help @{CHANNEL_HANDLE} Reach 100 Members!*\n\n"
        f"👥 Current: *{count}* | Goal: *100*\n\n"
        f"{esc_md(REFERRAL_REMINDER_MSG)}\n\n"
        "▫️ Refer 1 friend → 10 points\n"
        "▫️ Refer 5 friends → 1.5x points (15 each)\n"
        "▫️ Refer 10 friends → 2x points (20 each)\n\n"
        "👇 *Get your link:*\n"
        f"👉 @{esc_md(BOT_USERNAME)} and type /referral"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Get Your Referral Link", url=f"https://t.me/{BOT_USERNAME}?start=ref")],
        [InlineKeyboardButton("📤 Share Channel", url=f"https://t.me/share/url?url=https://t.me/{CHANNEL_HANDLE}&text=Join%20%40{CHANNEL_HANDLE}%21")]
    ])
    try:
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown", reply_markup=kb)
        log.info("Referral reminder sent to channel")
        if pin:
            try:
                await bot.pin_chat_message(chat_id=CHANNEL_ID, message_id=sent.message_id)
            except Exception:
                pass
    except Exception as e:
        log.error("Failed to send referral reminder: %s", e)

async def send_channel_welcome(bot: Bot):
    msg = (
        f"🎉 *Welcome!*\n\n{esc_md(WELCOME_MSG)}\n\n"
        f"👇 *Get started:*\n"
        f"🤖 @{esc_md(BOT_USERNAME)} → /start\n"
        f"📢 Share with friends → earn /referral\n\n"
        f"Let's grow together! 💰"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{BOT_USERNAME}?start=start")]])
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown", reply_markup=kb)
        log.info("Channel welcome posted")
    except Exception as e:
        log.error("Failed to send channel welcome: %s", e)

async def _reminder_job(context: ContextTypes.DEFAULT_TYPE):
    await post_referral_reminder(context.bot)

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.job_queue.run_repeating(_reminder_job, interval=14400, first=10)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(CONTENT_CMD, random_item))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("topdeal", topdeal))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("contact", contact))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    log.info("Bot started at @%s. Commands: /start /%s /topdeal /search <query> /referral /about /contact | Reminder every 4h", CHANNEL_ID.replace("@",""), CONTENT_CMD)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", action="store_true", help="Post & pin referral announcement")
    parser.add_argument("--welcome", action="store_true", help="Post welcome message to channel")
    parser.add_argument("--reminder", action="store_true", help="Post referral reminder once")
    parser.add_argument("--loop", action="store_true", help="Run reminder loop every 4 hours")
    args = parser.parse_args()
    if any([args.pin, args.welcome, args.reminder, args.loop]):
        async with Bot(token=BOT_TOKEN) as bot:
            if args.pin:
                await post_referral_reminder(bot, pin=True)
            if args.welcome:
                await send_channel_welcome(bot)
            if args.reminder:
                await post_referral_reminder(bot)
            if args.loop:
                log.info("Starting reminder loop...")
                while True:
                    await post_referral_reminder(bot)
                    await asyncio.sleep(14400)
    else:
        run_bot()

if __name__ == "__main__":
    asyncio.run(main())
