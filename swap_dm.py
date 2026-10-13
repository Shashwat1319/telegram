"""B5: Send channel-swap DMs to deals-channel admins from user's personal account.

Usage:
  py swap_dm.py --dry-run            # find admins, send nothing
  py swap_dm.py --limit 3            # send up to 3 DMs
  py swap_dm.py --limit 5 --force    # ignore previous state for this run
"""
import argparse, asyncio, logging, os, random, re, sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameNotOccupiedError, UserPrivacyRestrictedError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import ChannelParticipantsAdmins, User

from data import load_json, save_json

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("swap_dm")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_1")
IST = timezone(timedelta(hours=5, minutes=30))

STATE_FILE = "swap_dm_state.json"

TARGETS = [
    "@today_loot_offers",
    "@topdeaals",
    "@best_online_deals_for_you",
    "@uniqueofferszone",
    "@flashdealonline",
    "@deals_paytm",
    "@freeindiadeals",
    "@branddealsthree",
    "@tricksyloots",
    "@hotdealsanddiscounts",
    "@dhamakadealsdeliy",
    "@lootlinksdeals",
    "@proxdeals",
    "@amazondailydeals",
    # round 2 (2026-10-12, from WebGrupos search — similar-size Indian deals channels)
    "@amazon_flipkart_sale_offers_deal",
    "@DealsCouponsDiscounts",
    "@Festival_Deals_Offers",
    "@loudfashion",
    "@clotheshubindia",
    "@Only_Discounts_and_Offers_Deals",
    # round 3 (2026-10-12, WebGrupos deals page 2)
    "@Dealsxdeals",
    "@CreditCardDeals",
    "@DealshubBroadcast",
    "@looting_deals_offers_mega_best",
    "@flipkart_amazon_big_deals",
    # round 4 (2026-10-12, TgramLink #Deals + global search)
    "@babajishopingdeals",
    "@LootersZone_Official",
    "@dealwalepandit",
    "@gadgetwala",
    "@stardealz",
    "@lootsforall",
    "@gvcdeals",
    "@lqoffers",
    "@mr_sandeep",
    "@crazydealsalert",
    # round 5 (2026-10-12, admins of OUR joined deals groups — direct USER targets, bios verified deals-channels)
    "@Spencerji",        # runs @lootdeals144
    "@bosssisback",      # runs @dealzhubstar
    "@CaptainJarvis",    # offersbase.in
    "@Mr_rexx123",       # mobile deals channel
    "@Ankit_Kumar8540",  # mobile booking
    "@dhruvgarg9136",    # mobilebookergroup
    "@abhayagarwal",     # offerforall29
    "@todaydealstore",   # shoplootoffers
    "@yourshopdeal",     # shopalldeals
    "@saitej235",        # classydealss
    "@ankit704",         # mobile&tv booking
    "@DealsAdminOK",
]
TARGETS = list(dict.fromkeys(TARGETS))  # dedupe (O(1) membership via set below)
_SKIP = frozenset(("sent", "no_admin_username", "blocked", "error", "only_bot_admins",
                   "privacy_restricted", "bad_username", "not_a_channel", "target_is_bot"))

MSG = (
    "Hey! Love your channel. I run @smartgahr — an automated Amazon deals "
    "channel (Home & Kitchen, 40-80% off, all under ₹999).\n\n"
    "Want to do a mutual mention? I'll pin a post about your channel for 24h, "
    "you do the same. No strings attached.\n\n"
    "Let me know!"
)

def _now():
    return datetime.now(IST).isoformat(timespec="seconds")

async def _find_admin_username(client, entity, allow_join=True):
    """Return (username, n_admins, err) — join channel first, then list admins, filter bots."""
    if isinstance(entity, User):
        # direct USER target (round 5: group admins with deals bios) — the target IS the person
        if entity.bot:
            return None, 0, "target_is_bot"
        if not entity.username:
            return None, 0, "bad_username"
        return entity.username, 0, None
    # 1) join if we can (public channels) — participant listing needs membership.
    #    allow_join=False for targets we deliberately LEFT during cleanup (bio/message
    #    scan below still works for public channels without membership).
    if allow_join:
        try:
            await client(JoinChannelRequest(entity))
            await asyncio.sleep(2)
        except Exception as e:
            log.debug("join %s: %s", getattr(entity, "username", entity), type(e).__name__)

    # 2) admins (skip bots like MissRose)
    admins = []
    try:
        admins = await client.get_participants(entity, filter=ChannelParticipantsAdmins)
    except Exception as e:
        log.debug("admins %s: %s", getattr(entity, "username", entity), type(e).__name__)
    for a in admins:
        if getattr(a, "bot", False):
            continue
        if getattr(a, "username", None):
            try:
                full = await client.get_entity(a.username)
                if isinstance(full, User) and not full.bot:
                    return full.username, len(admins), None
            except Exception:
                continue

    # 3) fallback: channel bio (about) — try EVERY @handle / t.me link, skip dead/bots
    try:
        from telethon.tl.functions.channels import GetFullChannelRequest as _GFC
        full = await client(_GFC(entity))
        about = (full.full_chat.about or "") if full.full_chat else ""
        cands = set(re.findall(r"@([A-Za-z][\w\d]{3,30}[A-Za-z\d])", about))
        cands.update(re.findall(r"t\.me/([A-Za-z][\w\d]{3,30}[A-Za-z\d])", about))
        cands.discard(getattr(entity, "username", None) or "")
        for cand in sorted(cands):
            try:
                u = await client.get_entity(cand)
                if isinstance(u, User) and not u.bot:
                    return u.username, len(admins), None
            except Exception:
                continue
    except Exception as e:
        log.debug("bio %s: %s", getattr(entity, "username", entity), type(e).__name__)

    # 4) last resort: scan recent channel posts for @handles / t.me links
    try:
        async for m in client.iter_messages(entity, limit=100):
            if not m.message:
                continue
            cands = set(re.findall(r"@([A-Za-z][\w\d]{3,30}[A-Za-z\d])", m.message))
            cands.update(re.findall(r"t\.me/([A-Za-z][\w\d]{3,30}[A-Za-z\d])", m.message))
            cands.discard(getattr(entity, "username", None) or "")
            for cand in sorted(cands):
                try:
                    u = await client.get_entity(cand)
                    if isinstance(u, User) and not u.bot:
                        return u.username, len(admins), None
                except Exception:
                    continue
    except Exception as e:
        log.debug("scan %s: %s", getattr(entity, "username", entity), type(e).__name__)

    if admins:
        return None, len(admins), "only_bot_admins"
    return None, len(admins), "no_admin_username"

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="max DMs this run")
    ap.add_argument("--dry-run", action="store_true", help="find admins only, send nothing")
    ap.add_argument("--force", action="store_true", help="retry targets even if already handled")
    args = ap.parse_args()

    if not API_ID or not API_HASH or not SESSION_STR:
        log.error("API_ID/API_HASH/TELEGRAM_SESSION_1 missing in .env")
        sys.exit(1)

    state = load_json(STATE_FILE, {}) or {}
    client = TelegramClient(StringSession(SESSION_STR), int(API_ID), API_HASH, timeout=60)
    await client.start()
    who = await client.get_me()
    log.info("Logged in as %s (id=%s)", who.username or who.first_name, who.id)

    sent = 0
    for handle in TARGETS:
        prev = state.get(handle) or {}
        if not args.force and prev.get("status") in _SKIP:
            continue
        if sent >= args.limit:
            log.info("Limit %d reached — stopping", args.limit)
            break
        try:
            entity = await client.get_entity(handle)
            prev = state.get(handle) or {}
            username, n_admins, err = await _find_admin_username(client, entity, allow_join=prev.get("status") != "left")
            if err or not username:
                state[handle] = {"status": err or "no_admin_username", "at": _now()}
                log.warning("%s -> %s (admins=%s)", handle, state[handle]["status"], n_admins)
                continue
            if args.dry_run:
                state[handle] = {"status": "found_admin", "admin": username, "at": _now()}
                log.info("%s -> admin @%s (DRY RUN, not sent)", handle, username)
            else:
                await client.send_message(username, MSG)
                state[handle] = {"status": "sent", "admin": username, "at": _now()}
                log.info("%s -> DM SENT to @%s", handle, username)
                sent += 1
                await asyncio.sleep(random.randint(60, 120))
        except FloodWaitError as e:
            log.warning("Flood wait %ss — sleeping", e.seconds)
            await asyncio.sleep(e.seconds + 5)
        except UserPrivacyRestrictedError:
            state[handle] = {"status": "privacy_restricted", "at": _now()}
            log.warning("%s -> privacy restricted", handle)
        except UsernameNotOccupiedError:
            state[handle] = {"status": "bad_username", "at": _now()}
            log.warning("%s -> username not occupied", handle)
        except Exception as e:
            state[handle] = {"status": "error", "error": f"{type(e).__name__}: {e}"[:200], "at": _now()}
            log.error("%s -> ERROR %s", handle, e)
        save_json(STATE_FILE, state)

    save_json(STATE_FILE, state)
    counts = {}
    for v in state.values():
        counts[v.get("status", "?")] = counts.get(v.get("status", "?"), 0) + 1
    log.info("Summary: %s | sent this run: %d", counts, sent)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
