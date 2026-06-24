import os, logging, asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CLEAN_ID = CHANNEL_ID.replace("@", "") if CHANNEL_ID else "budgetdeals_india"
BOT_USERNAME = os.getenv("BOT_USERNAME", "Ffzon_bot")

REFERRAL_MSG = (
    "🎯 *Earn Rewards by Inviting Friends!*\n\n"
    "Share your unique referral link and earn points when friends join.\n\n"
    "▫️ Refer 1 friend → 10 points\n"
    "▫️ Refer 5 friends → 1.5x points (15 each)\n"
    "▫️ Refer 10 friends → 2x points (20 each)\n\n"
    "👇 *Get your link:*\n"
    f"👉 @{BOT_USERNAME.replace('_', '\\_')} and type /referral\n\n"
    "Let's grow this community together! 🚀"
)

WELCOME_MSG = (
    "🎉 *Welcome to Budget Deals India!*\n\n"
    "We post handpicked Amazon India deals daily — up to 70% OFF.\n\n"
    "🔹 New deals every 30 mins\n"
    "🔹 Verified prices & direct buy links\n"
    "🔹 Price drops you won't find elsewhere\n\n"
    "👇 *Get started:*\n"
    f"🤖 @{BOT_USERNAME.replace('_', '\\_')} → /start\n"
    "📢 Share with friends → earn /referral\n\n"
    "Let's save money together! 💰"
)


async def post_pinned():
    async with Bot(token=BOT_TOKEN) as bot:
        await bot.initialize()
        chat_id = f"@{CLEAN_ID}"

        log.info("Posting referral announcement to %s...", chat_id)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Get Your Referral Link", url=f"https://t.me/{BOT_USERNAME}?start=ref")],
            [InlineKeyboardButton("📤 Share Channel", url=f"https://t.me/share/url?url=https://t.me/{CLEAN_ID}&text=Join%20%40{CLEAN_ID}%20for%20daily%20Amazon%20deals%21")]
        ])

        sent = await bot.send_message(
            chat_id=chat_id,
            text=REFERRAL_MSG,
            parse_mode="Markdown",
            reply_markup=kb
        )
        log.info("Referral announcement posted! Message ID: %s", sent.message_id)

        try:
            await bot.pin_chat_message(chat_id=chat_id, message_id=sent.message_id)
            log.info("Message pinned successfully!")
        except Exception as e:
            log.warning("Could not pin: %s (bot needs admin rights)", e)

        await bot.shutdown()


async def send_welcome():
    async with Bot(token=BOT_TOKEN) as bot:
        await bot.initialize()
        chat_id = f"@{CLEAN_ID}"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{BOT_USERNAME}?start=start")]
        ])

        sent = await bot.send_message(
            chat_id=chat_id,
            text=WELCOME_MSG,
            parse_mode="Markdown",
            reply_markup=kb
        )
        log.info("Welcome message posted! Message ID: %s", sent.message_id)
        await bot.shutdown()


async def post_referral_reminder():
    async with Bot(token=BOT_TOKEN) as bot:
        await bot.initialize()
        chat_id = f"@{CLEAN_ID}"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Get Your Link", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        sent = await bot.send_message(
            chat_id=chat_id,
            text=REFERRAL_MSG,
            parse_mode="Markdown",
            reply_markup=kb
        )
        log.info("Referral reminder posted! Message ID: %s", sent.message_id)
        await bot.shutdown()


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", action="store_true", help="Post & pin referral announcement")
    parser.add_argument("--welcome", action="store_true", help="Post welcome message")
    parser.add_argument("--reminder", action="store_true", help="Post referral reminder")
    parser.add_argument("--loop", action="store_true", help="Run reminder loop every 4 hours")
    args = parser.parse_args()

    if args.pin:
        await post_pinned()
    elif args.welcome:
        await send_welcome()
    elif args.reminder:
        await post_referral_reminder()
    elif args.loop:
        log.info("Starting referral reminder loop...")
        while True:
            await post_referral_reminder()
            log.info("Next reminder in 4 hours...")
            await asyncio.sleep(4 * 3600)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
