import os, json, random, logging, asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from utils import get_price_value, format_price, calc_discount
from referral_manager import generate_referral_link, get_user_stats

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CLEAN_ID = CHANNEL_ID.replace("@", "") if CHANNEL_ID else "budgetdeals_india"
BOT_USERNAME = os.getenv("BOT_USERNAME", "Ffzon_bot")


def esc_md(text):
    return text.replace("_", "\\_")


def load_products():
    if not os.path.exists("product.json"):
        return []
    try:
        return json.load(open("product.json", encoding="utf-8"))["products"]
    except:
        return []


def get_latest_deal():
    products = load_products()
    if not products:
        return None
    posted = {}
    if os.path.exists("posted_products.json"):
        try:
            posted = json.load(open("posted_products.json"))
        except:
            pass
    unposted = [p for p in products if p.get("name") not in posted]
    pool = unposted if unposted else products
    return random.choice(pool)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = (
        f"👋 *Welcome {user.first_name}!*\n\n"
        f"I'm the *Budget Deals India* bot. I send handpicked Amazon deals "
        f"to @{esc_md(CLEAN_ID)} daily.\n\n"
        f"📌 *What you can do:*\n"
        f"• /deal — Get today's hottest deal\n"
        f"• /referral — Get your invite link & earn rewards\n"
        f"• /stats — Channel growth stats\n\n"
        f"Join @{esc_md(CLEAN_ID)} and never overpay on Amazon again! 🚀\n\n"
        f"💡 *Refer 5 friends → 1.5x points | Refer 10 → 2x points*"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CLEAN_ID}")],
        [InlineKeyboardButton("🔥 Latest Deal", callback_data="deal")],
        [InlineKeyboardButton("🎯 Get Referral Link", url=f"https://t.me/{BOT_USERNAME}?start=ref")]
    ])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


async def deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product = get_latest_deal()
    if not product:
        await update.message.reply_text("No deals available right now. Check back soon!")
        return

    name = product.get("name", "Amazing Deal")
    price = format_price(product.get("price", "Check"))
    mrp = product.get("mrp", "")
    drop = calc_discount(product.get("price", "0"), product.get("mrp", "0"))
    link = product.get("link", f"https://t.me/{CLEAN_ID}")
    rating = product.get("rating", "")
    img = product.get("image", "")

    msg = (
        f"🔥 *HOT DEAL*\n\n"
        f"*{name[:60]}*\n"
        f"~~{mrp}~~ → *{price}* ({drop}% OFF)\n"
    )
    if rating:
        msg += f"⭐ Rating: {rating}\n"
    msg += f"\n👉 [Buy on Amazon]({link})\n\n📢 Join @{esc_md(CLEAN_ID)} for more!"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", url=link)],
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CLEAN_ID}")]
    ])

    if img:
        try:
            await update.message.reply_photo(photo=img, caption=msg, parse_mode="Markdown", reply_markup=kb)
            return
        except:
            pass
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        link = await generate_referral_link(user.id)
        _, count, points = get_user_stats(user.id)
    except Exception as e:
        log.error("Referral error for user %d: %s", user.id, e)
        await update.message.reply_text(
            "❌ Could not generate referral link right now. "
            "Make sure the bot is admin in the channel. Try again later."
        )
        return

    msg = (
        f"🎯 *Your Referral Link*\n\n"
        f"Share this link with friends — when they join, you earn points!\n\n"
        f"🔗 `{link}`\n\n"
        f"📊 *Your Stats:*\n"
        f"• People referred: *{count}*\n"
        f"• Points earned: *{points}*\n\n"
        f"👥 Refer 5 → 1.5x points | Refer 10 → 2x points!"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}&text=Join%20%40{CLEAN_ID}%20for%20daily%20Amazon%20deals%21")],
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CLEAN_ID}")]
    ])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = load_products()
    product_count = len(products)

    channel_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id=@{CLEAN_ID}"
    members = "N/A"
    try:
        import requests
        r = requests.get(channel_url, timeout=5)
        if r.status_code == 200:
            members = r.json().get("result", "N/A")
    except:
        pass

    total_clicks = "N/A"
    tracker_url = os.getenv("CLICK_TRACKER_URL", "")
    if tracker_url:
        try:
            import requests
            r = requests.get(f"{tracker_url}/stats", timeout=5)
            if r.status_code == 200:
                data = r.json()
                total_clicks = data.get("total_clicks", "N/A")
        except:
            pass

    msg = (
        f"📊 *Channel Stats*\n\n"
        f"👥 *Members:* {members}\n"
        f"📦 *Deals in Queue:* {product_count}\n"
        f"👆 *Total Clicks:* {total_clicks}\n"
        f"📢 *Channel:* @{esc_md(CLEAN_ID)}\n\n"
        f"Keep sharing your referral link to earn rewards!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "deal":
        await deal(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.error("Update %s caused error: %s", update, context.error)


async def referral_reminder(context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Get Your Referral Link", url=f"https://t.me/{BOT_USERNAME}")],
        [InlineKeyboardButton("📤 Share Channel", url=f"https://t.me/share/url?url=https://t.me/{CLEAN_ID}&text=Join%20%40{CLEAN_ID}%20for%20daily%20Amazon%20deals%21")]
    ])
    msg = (
        "🎯 *Earn Rewards by Inviting Friends!*\n\n"
        "Share your unique referral link and earn points when friends join.\n\n"
        f"▫️ Refer 1 friend → 10 points\n"
        f"▫️ Refer 5 friends → 1.5x points (15 each)\n"
        f"▫️ Refer 10 friends → 2x points (20 each)\n\n"
        f"👇 *Get your link:*\n"
        f"👉 @{esc_md(BOT_USERNAME)} and type /referral"
    )
    try:
        chat_id = f"@{CLEAN_ID}"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=kb)
        log.info("Referral reminder sent to channel")
    except Exception as e:
        log.error("Failed to send referral reminder: %s", e)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deal", deal))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    job_queue = app.job_queue
    job_queue.run_repeating(referral_reminder, interval=14400, first=10)

    log.info("Bot started. Commands: /start /deal /referral /stats | Referral reminder every 4h")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
