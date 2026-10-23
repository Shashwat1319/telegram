"""Phase 1/2: DM recently-seen members from member_pool.json. MANUAL ONLY.

Safety rules (ban = non-negotiable):
  - combined budget TOTAL_DAILY (default 4) across swap_dm + member_dm, IST day
  - 60-120s gaps; FloodWait <=120s sleeps and continues, >120s ABORTS
  - PeerFlood ABORTS the run (no retry, ever)
  - fresh last-seen re-check at send time (stale pool entries skipped)

Usage:
  py member_dm.py --dry-run           # select + fresh-status check, send nothing
  py member_dm.py --limit 1           # probe (Phase 1)
  py member_dm.py                     # daily run (default limit 2, clamped to budget)
"""
import argparse, asyncio, logging, os, random, sys, time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, PeerFloodError, UserPrivacyRestrictedError, UserIsBlockedError,
    InputUserDeactivatedError, UserNotMutualContactError, UsernameNotOccupiedError,
)
from telethon.sessions import StringSession
from telethon.tl.types import InputUser, User

from data import load_json, save_json

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("member_dm")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_1")
IST = timezone(timedelta(hours=5, minutes=30))

POOL_FILE = "member_pool.json"
STATE_FILE = "member_dm_state.json"
SWAP_STATE_FILE = "swap_dm_state.json"
TOTAL_DAILY = 4            # combined swap_dm + member_dm per IST day
DEFAULT_LIMIT = 2          # member DMs per run
DEFAULT_OFFLINE_HOURS = 72 # freshness window re-checked at send time
REFRESH_ABOVE_HOURS = 96   # reskip if pool entry older than this
PREF_GROUPS = ["@magicpinofferss", "@mutualdeals", "@buysellbazaar", "@offerforall12"]


def _now():
    return datetime.now(IST).isoformat(timespec="seconds")


def _is_recent(status, offline_hours):
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
    return False


def _dms_used_today():
    """DMs already sent TODAY (IST) by swap_dm + member_dm."""
    today = datetime.now(IST).date().isoformat()
    n = 0
    detail = {"swap": 0, "member": 0}
    for path, bucket in ((SWAP_STATE_FILE, "swap"), (STATE_FILE, "member")):
        st = load_json(path, {}) or {}
        for v in st.values():
            if isinstance(v, dict) and v.get("status") == "sent" and str(v.get("at", ""))[:10] == today:
                n += 1
                detail[bucket] += 1
    return n, detail


def _already_dmed(pool_entry, state, swap_state):
    uid = str(pool_entry["id"])
    if uid in state:
        return True
    uname = (pool_entry.get("username") or "").lower()
    if uname:
        for v in (swap_state or {}).values():
            if isinstance(v, dict) and v.get("status") == "sent" and str(v.get("admin", "")).lower() == uname:
                return True
    return False


def _msg(title):
    clean = title if title and not title.startswith("http") else "deals group"
    return (
        f"Hey! Main bhi {clean} me hoon. Roz verified Amazon loot deals track karta hoon "
        f"— under Rs.999, 40-80% off, fake MRP wale skip.\n\n"
        f"Ek chhota channel hai: https://t.me/smartgahr\n"
        f"Join kar lo, spam bilkul nahi hai."
    )


def _abort(reason):
    log.critical("ABORT: %s — no more DMs this run (state saved by caller)", reason)
    sys.exit(2)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--dry-run", action="store_true", help="select + fresh check, send nothing")
    ap.add_argument("--offline-hours", type=int, default=DEFAULT_OFFLINE_HOURS)
    ap.add_argument("--force", action="store_true", help="retry previously failed entries")
    args = ap.parse_args()

    if not API_ID or not API_HASH or not SESSION_STR:
        log.error("API_ID/API_HASH/TELEGRAM_SESSION_1 missing in .env")
        sys.exit(1)

    pool = load_json(POOL_FILE, {}) or {}
    if not pool:
        log.error("member_pool.json empty — run py member_scrape.py first")
        sys.exit(1)
    state = load_json(STATE_FILE, {}) or {}
    swap_state = load_json(SWAP_STATE_FILE, {}) or {}

    used, detail = _dms_used_today()
    remaining = max(TOTAL_DAILY - used, 0)
    eff_limit = min(args.limit, remaining)
    log.info("Budget: %d/%d used today (swap=%d member=%d) -> can send %d now",
             used, TOTAL_DAILY, detail["swap"], detail["member"], eff_limit)
    if eff_limit <= 0:
        log.info("Daily budget exhausted — nothing to do")
        sys.exit(0)

    client = TelegramClient(StringSession(SESSION_STR), int(API_ID), API_HASH, timeout=60)
    await client.start()
    who = await client.get_me()
    log.info("Logged in as %s (id=%s)", who.username or who.first_name, who.id)

    # candidates: prefer big recent groups, then freshest scrape; skip done/older than REFRESH_ABOVE_HOURS
    fresh_cutoff = datetime.now(IST) - timedelta(hours=REFRESH_ABOVE_HOURS)
    cands = []
    for v in pool.values():
        if _already_dmed(v, state, swap_state):
            continue
        if not v.get("access_hash"):
            continue
        try:
            if datetime.fromisoformat(str(v.get("scraped_at"))) < fresh_cutoff:
                continue
        except Exception:
            continue
        pref = PREF_GROUPS.index(v["source_group"]) if v["source_group"] in PREF_GROUPS else 99
        cands.append((pref, str(v.get("scraped_at", "")), v))
    cands.sort(key=lambda x: (x[0], x[1]))
    log.info("Eligible pool: %d (state already has %d)", len(cands), len(state))

    sent = 0
    for _, _, entry in cands:
        if sent >= eff_limit:
            log.info("Limit %d reached — stopping", eff_limit)
            break
        uid = entry["id"]
        key = str(uid)
        try:
            fresh = await client.get_entity(InputUser(uid, entry["access_hash"]))
            if not isinstance(fresh, User) or getattr(fresh, "bot", False) or getattr(fresh, "self", False):
                state[key] = {"status": "not_user", "at": _now()}
                save_json(STATE_FILE, state)
                continue
            if not _is_recent(getattr(fresh, "status", None), args.offline_hours):
                state[key] = {"status": "stale", "at": _now()}
                save_json(STATE_FILE, state)
                log.info("skip stale last-seen: %s", entry.get("username") or uid)
                continue

            if args.dry_run:
                log.info("DRY RUN pick: @%s (%s, seen=%s) from %s",
                         fresh.username or "-", fresh.first_name or "?",
                         type(getattr(fresh, "status", None)).__name__, entry["source_group"])
                sent += 1
                continue

            msg = _msg(entry.get("source_title") or entry.get("source_group") or "deals group")
            await client.send_message(fresh, msg)
            sent += 1
            state[key] = {"status": "sent", "at": _now(), "group": entry.get("source_group"),
                          "username": fresh.username}
            save_json(STATE_FILE, state)
            log.info("DM SENT to @%s (from %s) [%d/%d today-total]",
                     fresh.username or uid, entry.get("source_group"), used + sent, TOTAL_DAILY)
            await asyncio.sleep(random.randint(60, 120))

        except FloodWaitError as e:
            save_json(STATE_FILE, state)
            if e.seconds > 120:
                _abort(f"FloodWait {e.seconds}s > 120s")
            log.warning("Flood wait %ss — sleeping", e.seconds)
            await asyncio.sleep(e.seconds + 5)
        except PeerFloodError:
            save_json(STATE_FILE, state)
            _abort("PeerFloodError — Telegram flagged DM volume, STOP for today (review before next run)")
        except UserPrivacyRestrictedError:
            state[key] = {"status": "privacy_restricted", "at": _now()}
            save_json(STATE_FILE, state)
            log.warning("privacy restricted: %s", entry.get("username") or uid)
        except (UserIsBlockedError, InputUserDeactivatedError, UserNotMutualContactError,
                UsernameNotOccupiedError) as e:
            state[key] = {"status": "error", "error": type(e).__name__, "at": _now()}
            save_json(STATE_FILE, state)
            log.warning("%s -> %s", entry.get("username") or uid, type(e).__name__)
        except Exception:
            state[key] = {"status": "error", "error": "see log", "at": _now()}
            save_json(STATE_FILE, state)
            raise

    if args.dry_run:
        log.info("Dry run complete: %d picks checked", sent)

    save_json(STATE_FILE, state)
    counts = {}
    for v in state.values():
        s = v.get("status", "?") if isinstance(v, dict) else "?"
        counts[s] = counts.get(s, 0) + 1
    used_now, _ = _dms_used_today()
    log.info("Summary: %s | sent this run: %d | day total: %d/%d",
             counts, sent, used_now, TOTAL_DAILY)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
