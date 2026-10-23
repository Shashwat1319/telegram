"""Phase 0: scrape recently-seen members of joined groups -> member_pool.json.

Read-only scrape: sends NO messages, joins/leaves nothing.

Usage:
  py member_scrape.py                  # scrape groups not rescraped in 7 days
  py member_scrape.py --force          # rescrape everything
  py member_scrape.py --groups @a,@b   # subset
  py member_scrape.py --offline-hours 72
"""
import argparse, asyncio, logging, os, random, sys, time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatAdminRequiredError, UsernameNotOccupiedError
from telethon.sessions import StringSession

from data import load_json, save_json

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("member_scrape")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_1")
IST = timezone(timedelta(hours=5, minutes=30))

GROUPS_FILE = "joined_groups_state.json"
POOL_FILE = "member_pool.json"
SCRAPE_STATE_FILE = "member_scrape_state.json"
OUR_CHANNEL = "@smartgahr"
DEFAULT_OFFLINE_HOURS = 72
DEFAULT_MAX_PER_GROUP = 1000
RESCRAPE_DAYS = 7


def _now():
    return datetime.now(IST).isoformat(timespec="seconds")


def _is_recent(status, offline_hours):
    """True for Online / Recently / Offline within offline_hours. Uses type names
    so missing layer types can never crash the scrape."""
    if status is None:
        return False
    name = type(status).__name__
    if name in ("UserStatusOnline", "UserStatusRecently"):
        return True
    if name == "UserStatusOffline":
        wo = getattr(status, "was_online", None)
        if wo is None:
            return False
        try:
            ts = wo.timestamp() if hasattr(wo, "timestamp") else float(wo)
            return (time.time() - ts) <= offline_hours * 3600
        except Exception:
            return False
    return False  # LastWeek / LastMonth / Empty / unknown


def _seen_label(status):
    name = type(status).__name__
    if name == "UserStatusOffline":
        wo = getattr(status, "was_online", None)
        if wo is None:
            return "offline"
        try:
            return datetime.fromtimestamp(
                wo.timestamp() if hasattr(wo, "timestamp") else float(wo), IST
            ).isoformat(timespec="seconds")
        except Exception:
            return "offline"
    return name


def _target_groups(only, force, scrape_state, log_):
    groups = load_json(GROUPS_FILE, {}) or {}
    out = []
    for key, v in groups.items():
        if not isinstance(v, dict) or v.get("status") != "joined":
            continue
        if not str(key).startswith("@"):
            log_.info("skip (invite-link key, unresolvable): %s", key)
            continue
        if key == OUR_CHANNEL:
            continue
        if only and key not in only:
            continue
        prev = scrape_state.get(key) or {}
        age_days = None
        if prev.get("scraped_at") and not force:
            try:
                prev_dt = datetime.fromisoformat(prev["scraped_at"])
                age_days = (datetime.now(prev_dt.tzinfo) - prev_dt).total_seconds() / 86400
            except Exception:
                age_days = None
            if age_days is not None and age_days < RESCRAPE_DAYS:
                log_.info("skip fresh (%.1fd old, %d recent): %s", age_days, prev.get("recent", 0), key)
                continue
        out.append((key, v))
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline-hours", type=int, default=DEFAULT_OFFLINE_HOURS,
                    help="Offline<=N h counts as recent (default 72)")
    ap.add_argument("--max-per-group", type=int, default=DEFAULT_MAX_PER_GROUP)
    ap.add_argument("--force", action="store_true", help="rescrape even if fresh")
    ap.add_argument("--groups", default="", help="comma-separated @usernames (default: all joined)")
    args = ap.parse_args()

    if not API_ID or not API_HASH or not SESSION_STR:
        log.error("API_ID/API_HASH/TELEGRAM_SESSION_1 missing in .env")
        sys.exit(1)

    only = {g.strip() for g in args.groups.split(",") if g.strip()} or None
    pool = load_json(POOL_FILE, {}) or {}
    scrape_state = load_json(SCRAPE_STATE_FILE, {}) or {}
    targets = _target_groups(only, args.force, scrape_state, log)

    client = TelegramClient(StringSession(SESSION_STR), int(API_ID), API_HASH, timeout=60)
    await client.start()
    who = await client.get_me()
    log.info("Logged in as %s (id=%s) | pool already %d users | %d groups to scrape",
             who.username or who.first_name, who.id, len(pool), len(targets))

    our_members = set()
    try:
        async for m in client.iter_participants(OUR_CHANNEL, limit=500):
            our_members.add(m.id)
        log.info("Excluded set: %d members of %s", len(our_members), OUR_CHANNEL)
    except Exception as e:
        log.warning("Could not list %s members (exclude skipped): %s", OUR_CHANNEL, type(e).__name__)

    for gkey, gmeta in targets:
        title = str(gmeta.get("detail") or gkey)
        try:
            entity = await client.get_entity(gkey)
        except (UsernameNotOccupiedError, ChannelPrivateError, ValueError) as e:
            scrape_state[gkey] = {"scraped_at": _now(), "error": type(e).__name__, "returned": 0, "recent": 0}
            log.warning("%s: unresolvable (%s)", gkey, type(e).__name__)
            save_json(SCRAPE_STATE_FILE, scrape_state)
            continue

        returned = 0
        recent_n = 0
        err = None
        try:
            async for u in client.iter_participants(entity, limit=args.max_per_group):
                returned += 1
                if getattr(u, "bot", False) or getattr(u, "self", False) or u.id in our_members:
                    continue
                if not _is_recent(getattr(u, "status", None), args.offline_hours):
                    continue
                recent_n += 1
                pool[str(u.id)] = {
                    "id": u.id,
                    "access_hash": u.access_hash,
                    "username": getattr(u, "username", None),
                    "first_name": getattr(u, "first_name", None) or "",
                    "source_group": gkey,
                    "source_title": title,
                    "seen": _seen_label(getattr(u, "status", None)),
                    "scraped_at": _now(),
                }
            await asyncio.sleep(random.uniform(1.0, 2.0))
        except FloodWaitError as e:
            err = f"FloodWait:{e.seconds}"
            log.warning("%s: flood wait %ss — sleeping", gkey, e.seconds)
            await asyncio.sleep(min(e.seconds, 60) + 5)
        except (ChannelPrivateError, ChatAdminRequiredError) as e:
            err = type(e).__name__
            log.warning("%s: %s", gkey, err)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:150]
            log.error("%s: scrape error %s", gkey, err)

        scrape_state[gkey] = {"scraped_at": _now(), "returned": returned,
                              "recent": recent_n, "title": title, **({"error": err} if err else {})}
        save_json(POOL_FILE, pool)
        save_json(SCRAPE_STATE_FILE, scrape_state)
        log.info("%s: %d returned, %d recent -> pool %d", gkey, returned, recent_n, len(pool))

    # final report
    total_users = len(pool)
    by_group = {}
    for v in pool.values():
        g = v.get("source_group", "?")
        by_group[g] = by_group.get(g, 0) + 1
    seen_types = {}
    for v in pool.values():
        s = str(v.get("seen", "?"))
        k = "offline_le72h" if s.startswith("20") else s.replace("UserStatus", "").lower()
        seen_types[k] = seen_types.get(k, 0) + 1
    log.info("=== SCRAPE DONE === pool=%d | groups contributing=%d | seen breakdown=%s",
             total_users, len(by_group), seen_types)
    for g, n in sorted(by_group.items(), key=lambda x: -x[1]):
        log.info("  %-45s %d", g, n)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
