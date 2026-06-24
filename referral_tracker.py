import asyncio, os, json, argparse, logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION = os.getenv('TELEGRAM_SESSION_1')
CHANNEL_ID = os.getenv('CHANNEL_ID')
BOT_TOKEN = os.getenv('BOT_TOKEN')
REFERRAL_FILE = 'referrals.json'
CLEAN_ID = CHANNEL_ID.replace('@', '') if CHANNEL_ID else 'budgetdeals_india'


def load_referrals():
    if os.path.exists(REFERRAL_FILE):
        try:
            with open(REFERRAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_referrals(data):
    with open(REFERRAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def send_welcome(user_id: int, username: str = None):
    from telegram import Bot
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            await bot.initialize()
            mention = f"@{username}" if username else f"User"
            msg = (
                f"🎉 *Welcome to Budget Deals India, {mention}!*\n\n"
                f"We post handpicked *Amazon India deals* with up to 70% OFF "
                f"on electronics, fashion, home & more.\n\n"
                f"🔹 New deals posted every 30 mins\n"
                f"🔹 Verified prices & direct buy links\n"
                f"🔹 Price drops you won't find elsewhere\n\n"
                f"👇 *Get started:*\n"
                f"• /deal — See today's hottest deal\n"
                f"• /referral — Earn rewards by inviting friends\n"
                f"• /stats — Check channel growth\n\n"
                f"📢 Join the discussion: @{CLEAN_ID}"
            )
            await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
            await bot.shutdown()
    except Exception as e:
        log.warning("Could not send welcome to user %d: %s", user_id, e)


def record_join(invite_link: str, user_id: int, username: str = None):
    referrals = load_referrals()

    matched_link = None
    for link in referrals:
        if invite_link and (invite_link in link or link in invite_link):
            matched_link = link
            break

    if not matched_link:
        for link in referrals:
            if CLEAN_ID in link:
                matched_link = link
                break

    if matched_link:
        info = referrals[matched_link]
        if user_id not in info.get('joined', []):
            info.setdefault('joined', []).append(user_id)
            info['last_join'] = {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.utcnow().isoformat()
            }
            save_referrals(referrals)
            log.info("Referral: user %d (@%s) joined via %s... Total: %d",
                     user_id, username, matched_link[:50], len(info['joined']))
            return True
    return False


async def oneshot_check():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log.error("Session not authorized")
        return

    channel = CLEAN_ID
    try:
        participants = await client.get_participants(channel, limit=500)
        refs = load_referrals()

        new_joins = 0
        for p in participants:
            if not p.bot and not p.deleted:
                for link, info in refs.items():
                    if p.id not in info.get('joined', []):
                        info.setdefault('joined', []).append(p.id)
                        info['last_join'] = {
                            'user_id': p.id,
                            'username': p.username,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        new_joins += 1

        if new_joins > 0:
            save_referrals(refs)
            log.info("Oneshot: found %d new referral joins", new_joins)
        else:
            log.info("Oneshot: no new referral joins found")

    except Exception as e:
        log.error("Oneshot error: %s", e)
    finally:
        await client.disconnect()


async def event_listener():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    log.info("Referral tracker started as %s (@%s)", me.first_name, me.username)

    @client.on(events.ChatAction)
    async def handler(event):
        if event.user_joined or event.user_added:
            user = await event.get_user()
            if user and not user.bot and not user.deleted:
                invite_link = None
                if hasattr(event.action, 'invite') and event.action.invite:
                    invite_link = event.action.invite.link
                joined = record_join(invite_link or '', user.id, user.username)
                if joined:
                    await send_welcome(user.id, user.username)

    @client.on(events.Raw)
    async def raw_handler(update):
        if hasattr(update, 'user_id') and hasattr(update, 'invite'):
            invite_link = update.invite.link if update.invite else None
            joined = record_join(invite_link or '', update.user_id)
            if joined:
                await send_welcome(update.user_id)

    log.info("Listening for join events... (Ctrl+C to stop)")
    await client.run_until_disconnected()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--oneshot', action='store_true', help='Run one-shot check and exit')
    args = parser.parse_args()

    if args.oneshot:
        await oneshot_check()
    else:
        await event_listener()


if __name__ == '__main__':
    asyncio.run(main())
