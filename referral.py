import os, asyncio, logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from dotenv import load_dotenv
from config_loader import load_config
from data import load_json, save_json
from utils import esc_md

load_dotenv()
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Telethon credentials only needed for event_listener (not --oneshot)
# Lazy-loaded inside event_listener() to avoid crash on --oneshot
config = load_config().get("bot", {})
CHANNEL_HANDLE = config.get("channel_handle", "channel")
CHANNEL_ID = config.get("channel_id", os.getenv("CHANNEL_ID", "@channel"))
BOT_USERNAME = config.get("username", os.getenv("BOT_USERNAME", "YourBot"))
WELCOME_MSG = config.get("welcome_message", "Welcome!")
CONTENT_CMD = config.get("content_command", "random")
PREMIUM_CHANNEL = config.get("premium_channel_handle", "smartgahrpremium")
PREMIUM_UNLOCK = int(config.get("premium_unlock_referrals", 2))

REFERRAL_FILE = "referrals.json"
REFERRAL_REWARD_BASE = int(os.getenv("REFERRAL_REWARD_BASE", "10"))
REFERRAL_TIER_1_THRESHOLD = int(os.getenv("REFERRAL_TIER_1_THRESHOLD", "5"))
REFERRAL_TIER_2_THRESHOLD = int(os.getenv("REFERRAL_TIER_2_THRESHOLD", "10"))
PREMIUM_REFERRALS_NEEDED = int(os.getenv("PREMIUM_REFERRALS_NEEDED", "2"))
PREMIUM_DURATION_DAYS = int(os.getenv("PREMIUM_DURATION_DAYS", "30"))

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
        raise RuntimeError("Failed to create referral link")  # pragma: no cover

def get_user_stats(user_id: int):
    referrals = load_referrals()
    for link, info in referrals.items():
        if info.get("creator") == user_id:
            total_joined = len(info.get("joined", []))
            return link, total_joined, total_joined * REFERRAL_REWARD_BASE
    return None, 0, 0


def get_premium_status(user_id: int):
    """Returns (active, joined_count, expires_at_iso). Active = count >= needed and not expired."""
    referrals = load_referrals()
    for link, info in referrals.items():
        if info.get("creator") == user_id:
            count = len(info.get("joined", []))
            expires = info.get("premium_expires_at")
            active = False
            if count >= PREMIUM_REFERRALS_NEEDED:
                if expires:
                    try:
                        exp_dt = datetime.fromisoformat(expires)
                        if exp_dt.tzinfo is None:
                            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                        active = exp_dt > datetime.now(timezone.utc)
                    except Exception:
                        active = True
                else:
                    # First unlock: set expiry for the first time
                    active = True
            return active, count, expires
    return False, 0, None


def ensure_premium_expiry(user_id: int, force=False):
    """Sets premium_expires_at when a user crosses the threshold (now + duration)."""
    referrals = load_referrals()
    for link, info in referrals.items():
        if info.get("creator") == user_id:
            count = len(info.get("joined", []))
            if count >= PREMIUM_REFERRALS_NEEDED and (not info.get("premium_expires_at") or force):
                info["premium_expires_at"] = (datetime.now(timezone.utc) + timedelta(days=PREMIUM_DURATION_DAYS)).isoformat()
                save_referrals(referrals)
                log.info("Premium expiry set for user %d: %s", user_id, info["premium_expires_at"])
            return
    return

def record_join(invite_link: str, user_id: int, username: Optional[str] = None) -> bool:
    referrals = load_referrals()
    for link in referrals:
        if invite_link and invite_link.strip() == link.strip():
            info = referrals[link]
            if user_id not in info.get("joined", []):
                info.setdefault("joined", []).append(user_id)
                info["last_join"] = {"user_id": user_id, "username": username, "timestamp": datetime.now(timezone.utc).isoformat()}
                # Renew premium if threshold met
                if len(info["joined"]) >= PREMIUM_REFERRALS_NEEDED:
                    info["premium_expires_at"] = (datetime.now(timezone.utc) + timedelta(days=PREMIUM_DURATION_DAYS)).isoformat()
                save_referrals(referrals)
                log.info("Referral: user %d (@%s) joined via %s... Total: %d", user_id, username, link[:50], len(info["joined"]))
                return True
            return False
    return False

async def send_welcome(user_id: int, username: Optional[str] = None):
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            await bot.initialize()
            mention = esc_md(username) if username else "User"
            msg = (
                f"🎉 *Welcome, @{mention}!*\n\n{WELCOME_MSG}\n\n"
                f"👇 *Get started:*\n"
                f"• /{CONTENT_CMD} — See what's new\n"
                f"• /referral — Get your invite link\n\n"
                f"🎁 *FREE PREMIUM ACCESS*\n"
                f"Refer {PREMIUM_UNLOCK} friends → unlock secret deals channel @{esc_md(PREMIUM_CHANNEL)}!\n\n"
                f"📢 Join @{esc_md(CHANNEL_HANDLE)}"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 Get Referral Link", url=f"https://t.me/{BOT_USERNAME}?start=ref")],
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_HANDLE}")]
            ])
            await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        log.warning("Could not send welcome to user %d: %s", user_id, e)

async def event_listener():
    api_id_var = os.getenv("API_ID")
    if not api_id_var:
        log.error("API_ID environment variable is required for referral tracker")
        return
    api_id = int(api_id_var)
    api_hash = os.getenv("API_HASH")
    session_str = os.getenv("TELEGRAM_SESSION_1")
    if not api_hash or not session_str:
        log.error("API_HASH and TELEGRAM_SESSION_1 are required for referral tracker")
        return
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
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
