import os, asyncio, logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from config_loader import load_config
from data import load_json, save_json
from utils import esc_md

load_dotenv()
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID_VAR = os.getenv("API_ID")
if not API_ID_VAR:
    raise RuntimeError("API_ID environment variable is required")
API_ID = int(API_ID_VAR)
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("TELEGRAM_SESSION_1")
config = load_config().get("bot", {})
CHANNEL_HANDLE = config.get("channel_handle", "channel")
CHANNEL_ID = config.get("channel_id", os.getenv("CHANNEL_ID", "@channel"))
BOT_USERNAME = config.get("username", os.getenv("BOT_USERNAME", "YourBot"))
WELCOME_MSG = config.get("welcome_message", "Welcome!")
CONTENT_CMD = config.get("content_command", "random")

REFERRAL_FILE = "referrals.json"
REFERRAL_REWARD_BASE = int(os.getenv("REFERRAL_REWARD_BASE", "10"))
REFERRAL_TIER_1_THRESHOLD = int(os.getenv("REFERRAL_TIER_1_THRESHOLD", "5"))
REFERRAL_TIER_2_THRESHOLD = int(os.getenv("REFERRAL_TIER_2_THRESHOLD", "10"))

_LOCK = asyncio.Lock()

def load_referrals():
    return load_json(REFERRAL_FILE, default={})

def save_referrals(data):
    save_json(REFERRAL_FILE, data)

async def generate_referral_link(user_id: int) -> str:
    async with _LOCK:
        referrals = load_referrals()
        for link, info in referrals.items():
            if info.get("creator") == user_id:
                return link

        from telegram import Bot
        from telegram.error import TelegramError
        for attempt in range(3):
            try:
                async with Bot(token=BOT_TOKEN) as bot:
                    await bot.initialize()
                    inv = await bot.create_chat_invite_link(
                        chat_id=CHANNEL_ID,
                        name=f"ref_{user_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        creates_join_request=False, expire_date=None, member_limit=0)
                    await bot.shutdown()
                    link = inv.invite_link
                referrals[link] = {"creator": user_id, "created_at": datetime.now(timezone.utc).isoformat(), "joined": []}
                save_referrals(referrals)
                log.info("Created referral link for user %d", user_id)
                return link
            except TelegramError as e:
                log.warning("Attempt %d failed: %s", attempt + 1, e)
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                log.error("Unexpected error: %s", e)
                raise

def get_user_stats(user_id: int):
    referrals = load_referrals()
    for link, info in referrals.items():
        if info.get("creator") == user_id:
            total_joined = len(info.get("joined", []))
            return link, total_joined, total_joined * REFERRAL_REWARD_BASE
    return None, 0, 0

def record_join(invite_link: str, user_id: int, username: str = None):
    referrals = load_referrals()
    for link in referrals:
        if invite_link and invite_link.strip() == link.strip():
            info = referrals[link]
            if user_id not in info.get("joined", []):
                info.setdefault("joined", []).append(user_id)
                info["last_join"] = {"user_id": user_id, "username": username, "timestamp": datetime.now(timezone.utc).isoformat()}
                save_referrals(referrals)
                log.info("Referral: user %d (@%s) joined via %s... Total: %d", user_id, username, link[:50], len(info["joined"]))
                return True
            return False
    return False

async def send_welcome(user_id: int, username: str = None):
    from telegram import Bot
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            await bot.initialize()
            mention = esc_md(username) if username else "User"
            msg = (
                f"🎉 *Welcome, @{mention}!*\n\n{WELCOME_MSG}\n\n"
                f"👇 *Get started:*\n"
                f"• /{CONTENT_CMD} — See what's new\n"
                f"• /referral — Earn rewards by inviting friends\n\n"
                f"📢 Join @{esc_md(CHANNEL_HANDLE)}"
            )
            await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        log.warning("Could not send welcome to user %d: %s", user_id, e)

async def event_listener():
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    log.info("Referral tracker started as %s (@%s)", me.first_name, me.username)

    @client.on(events.ChatAction)
    async def handler(event):
        if event.user_joined or event.user_added:
            user = await event.get_user()
            if user and not user.bot and not user.deleted:
                invite_link = getattr(getattr(event.action, "invite", None), "link", None)
                if record_join(invite_link or "", user.id, user.username):
                    await send_welcome(user.id, user.username)

    @client.on(events.Raw)
    async def raw_handler(update):
        if hasattr(update, "user_id") and hasattr(update, "invite"):
            invite_link = getattr(update.invite, "link", None)
            if record_join(invite_link or "", update.user_id):
                await send_welcome(update.user_id)

    log.info("Listening for join events...")
    await client.run_until_disconnected()

def calculate_rewards() -> dict:
    referrals = load_referrals()
    rewards = {}
    for info in referrals.values():
        creator = info.get("creator")
        count = len(info.get("joined", []))
        multiplier = 2.0 if count >= REFERRAL_TIER_2_THRESHOLD else 1.5 if count >= REFERRAL_TIER_1_THRESHOLD else 1.0
        rewards[creator] = rewards.get(creator, 0) + int(count * REFERRAL_REWARD_BASE * multiplier + 0.5)
    return rewards


if __name__ == "__main__":
    import sys
    if "--oneshot" in sys.argv:
        refs = load_referrals()
        rewards = calculate_rewards()
        print(f"Referrals: {len(refs)} users, {sum(len(r.get('joined',[])) for r in refs.values())} joins")
        for uid, reward in rewards.items():
            print(f"  {uid}: ₹{reward}")
    else:
        asyncio.run(event_listener())
