"""Auto-join promo groups so the user account can post deals in them.

Reads @usernames AND t.me/+ invite links from verified_promo_groups.txt and
discovered_groups.txt, joins each public group/channel with a random pace
(anti-flood), records status per entry, and optionally probes whether we have
send rights (so group_poster only targets writable chats). Entries marked
send=blocked (kicked earlier) are re-attempted.

Quality scoring (2026-10-24): after every join the group's title + description
are scored for buyer signals (deal/loot/offer/...) vs junk signals
(earn/MLM/promotion/...). Result stored as entry.quality = buyer|neutral|junk
+ entry.score (0-10) + entry.title/entry.members. group_poster skips junk and
rotates buyer groups first.

Daily cap: at most content.group_joins_per_day attempts per UTC day (default
12) so the session never mass-joins in one burst.

Usage:
    py join_promo_groups.py            # join due entries (capped by daily limit)
    py join_promo_groups.py --probe    # also probe send rights after joining
    py join_promo_groups.py --limit 10 # join at most 10 new entries
    py join_promo_groups.py --max-joins 5   # override daily cap for this run
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    UsernameNotOccupiedError,
    UserAlreadyParticipantError,
)
from telethon.sessions import StringSession

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("join_promo")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_1")

GROUPS_FILE = "verified_promo_groups.txt"
DISCOVERED_FILE = "discovered_groups.txt"
STATE_FILE = "joined_groups_state.json"

JOIN_DELAY_MIN = 25
JOIN_DELAY_MAX = 60
DEFAULT_JOINS_PER_DAY = 12

INVITE_RE = re.compile(r"(?:https?://)?t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]+)")

# Quality-scoring keyword sets (word-boundary, case-insensitive).
BUYER_RE = re.compile(
    r"\b(?:deals?|loot|offers?|discounts?|sale|shopping|shop|amazon|flipkart|"
    r"prices?|coupons?|cashback|budget|savings?|save|reviews?|clearance|"
    r"bargain|freebies?)\b",
    re.IGNORECASE,
)
JUNK_RE = re.compile(
    r"\b(?:earn|earning|income|investment|invest|trading|trader|betting|"
    r"gambling|casino|mlm|network marketing|digital marketing|promote|"
    r"promotion|advertising|sub4sub|followers|crypto|forex|porn|sex|18\+|"
    r"hiring|jobs?|part time|work from home|wfh|spam)\b",
    re.IGNORECASE,
)


def score_group(title, desc=""):
    """Heuristic buyer/junk score from group title + description.

    Returns (score 0-10, quality in buyer|neutral|junk).
    junk requires >=2 junk hits that are >= buyer hits (single keyword like
    "promotion" in an otherwise legit title must not nuke the group)."""
    text = f"{title or ''} {desc or ''}"
    buyer = len({m.group(0).lower() for m in BUYER_RE.finditer(text)})
    junk = len({m.group(0).lower() for m in JUNK_RE.finditer(text)})
    score = 5 + 2 * min(buyer, 3) - 4 * min(junk, 3)
    score = max(0, min(10, score))
    if junk >= 2 and junk >= buyer:
        quality = "junk"
    elif buyer >= 2 and buyer > junk:
        quality = "buyer"
    else:
        quality = "neutral"
    return score, quality


def _joins_today_cap():
    try:
        from config_loader import load_config
        return max(1, int(load_config().get("content", {}).get("group_joins_per_day", DEFAULT_JOINS_PER_DAY)))
    except Exception:
        return DEFAULT_JOINS_PER_DAY


def _attempts_today(state):
    today = datetime.now(timezone.utc).date().isoformat()
    n = 0
    for e in state.values():
        if isinstance(e, dict) and str(e.get("at") or "")[:10] == today:
            n += 1
    return n



def load_groups():
    out = []
    found = False
    for path in (GROUPS_FILE, DISCOVERED_FILE):
        if not os.path.exists(path):
            continue
        found = True
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    out.append(line)
    if not found:
        log.error("%s not found", GROUPS_FILE)
    seen = set()
    deduped = []
    for g in out:
        if g not in seen:
            seen.add(g)
            deduped.append(g)
    return deduped


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


async def join_one(client, username):
    """Join a public chat by username or invite link. Returns (status, detail, entity|None)."""
    m = INVITE_RE.search(username)
    if m:
        entity = None
        try:
            updates = await asyncio.wait_for(client(ImportChatInviteRequest(m.group(1))), timeout=30)
        except UserAlreadyParticipantError:
            return "already", "member", None
        except FloodWaitError as e:
            return "floodwait", str(e.seconds), None
        except Exception as e:
            return "error", f"{type(e).__name__}: {e}", None
        try:
            chats = getattr(updates, "chats", None) or []
            entity = chats[0] if chats else None
        except Exception:
            entity = None
        return "joined", "invite link", entity
    try:
        entity = await asyncio.wait_for(client.get_entity(username), timeout=30)
        try:
            await asyncio.wait_for(client(JoinChannelRequest(entity)), timeout=30)
        except UserAlreadyParticipantError:
            return "already", "member", entity
        except FloodWaitError as e:
            return "floodwait", str(e.seconds), entity
        return "joined", getattr(entity, "title", username), entity
    except UsernameNotOccupiedError:
        return "not_found", "username does not exist", None
    except ChannelPrivateError:
        return "private", "invite only", None
    except FloodWaitError as e:
        return "floodwait", str(e.seconds), None
    except Exception as e:
        return "error", f"{type(e).__name__}: {e}", None


async def describe(client, group, entity=None):
    """Best-effort (title, about, members) for quality scoring.

    Light entities often lack `about`/participant counts — fall back to the
    full-chat fetch exactly like group_poster._sort_by_members does."""
    try:
        if entity is None:
            entity = await asyncio.wait_for(client.get_entity(group), timeout=30)
        title = getattr(entity, "title", None) or ""
        about = getattr(entity, "about", None) or ""
        members = getattr(entity, "participants_count", None)
        if not about or not isinstance(members, int):
            cls = entity.__class__.__name__
            try:
                if cls == "Chat":
                    from telethon.tl.functions.messages import GetFullChatRequest
                    full = await asyncio.wait_for(client(GetFullChatRequest(entity.id)), timeout=30)
                else:
                    from telethon.tl.functions.channels import GetFullChannelRequest
                    full = await asyncio.wait_for(client(GetFullChannelRequest(entity)), timeout=30)
                about = about or getattr(full.full_chat, "about", "") or ""
                if not isinstance(members, int):
                    members = getattr(full.full_chat, "participants_count", None)
            except Exception:
                pass
        return title, about, members
    except Exception:
        return "", "", None


async def probe_send(client, username):
    """Check if we can send messages in the chat without actually posting."""
    try:
        entity = await asyncio.wait_for(client.get_entity(username), timeout=30)
        if getattr(entity, "broadcast", False):
            return "channel_no_post", "channel (need admin to post)"
        me = await client.get_me()
        perms = await client.get_permissions(entity, me)
        if perms is None:
            return "unknown", "no perms returned"
        if getattr(perms, "is_banned", False):
            return "banned", "banned member"
        if getattr(perms, "is_creator", False) or getattr(perms, "is_admin", False):
            return "writable", "admin/owner"
        if getattr(entity, "broadcast", False):
            return "channel_no_post", "channel (need admin to post)"
        return "writable", "member (best effort)"
    except Exception as e:
        return "error", f"{type(e).__name__}: {e}"


from telethon.tl.functions.channels import JoinChannelRequest  # noqa: E402
from telethon.tl.functions.messages import ImportChatInviteRequest  # noqa: E402


def _due_join(entry):
    """Retry failed joins only after 7 days; floodwait always retries.
    Entries we deliberately LEFT (cleanup) are NEVER re-joined — mass-rejoining
    100+ junk groups would undo the cleanup and risk an account ban."""
    if not entry:
        return True
    if entry.get("status") == "floodwait":
        return True
    if entry.get("status") in ("joined", "already", "left"):
        return False
    if entry.get("send") == "left":
        return False
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(entry.get("at"))
        return age.days >= 7
    except Exception:
        return True


async def main():
    if not API_ID or not API_HASH or not SESSION_STR:
        log.error("API_ID/API_HASH/TELEGRAM_SESSION_1 missing")
        return 1

    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="probe send rights after join")
    ap.add_argument("--limit", type=int, default=0, help="max new joins this run")
    ap.add_argument("--max-joins", type=int, default=0, help="override daily join cap for this run")
    ap.add_argument("--no-cap", action="store_true", help="ignore the daily join cap (use with care)")
    args = ap.parse_args()

    groups = load_groups()
    state = load_state()
    log.info("Loaded %d groups, %d already in state", len(groups), len(state))

    todo = [
        g for g in groups
        if _due_join(state.get(g) or {}) or state.get(g, {}).get("send") == "blocked"
    ]
    if args.limit:
        todo = todo[: args.limit]

    # Daily anti-flood cap: bound join attempts per UTC day regardless of queue size.
    if args.no_cap:
        log.warning("Daily join cap DISABLED for this run (--no-cap)")
    else:
        cap = args.max_joins if args.max_joins > 0 else _joins_today_cap()
        used = _attempts_today(state)
        if used >= cap:
            log.info("Daily join cap reached (%d/%d attempts today) — nothing to do", used, cap)
            return 0
        budget = cap - used
        if len(todo) > budget:
            log.info("Capping todo: %d entries fit in today's budget (%d/%d used)", budget, used, cap)
            todo = todo[:budget]

    log.info("%d entries to join/re-join", len(todo))

    if not todo:
        log.info("Nothing to join")
        return 0

    client = TelegramClient(StringSession(SESSION_STR), int(API_ID), API_HASH, timeout=30)
    await asyncio.wait_for(client.connect(), timeout=45)
    try:
        if not await client.is_user_authorized():
            log.error("Session not authorized")
            return 1
        me = await client.get_me()
        log.info("Logged in as %s", me.first_name or me.phone)

        for i, group in enumerate(todo):
            status, detail, entity = await join_one(client, group)
            old = state.get(group) or {}
            entry = dict(old)  # preserve send/paused/quality/members across retries
            entry.update({
                "status": status,
                "detail": detail[:120],
                "at": datetime.now(timezone.utc).isoformat(),
            })
            if old.get("members") is not None:
                entry["members"] = old["members"]
                entry["members_at"] = old.get("members_at")
            is_invite = bool(INVITE_RE.search(group))
            if args.probe and status in ("joined", "already") and not is_invite:
                p_status, p_detail = await probe_send(client, group)
                entry["send"] = p_status
                entry["send_detail"] = p_detail[:120]
            elif status in ("joined", "already"):
                entry.pop("send", None)
            if status in ("joined", "already"):
                # Quality scoring — fresh entity metadata on every successful join.
                title, about, members = await describe(client, group, entity)
                if title or about:
                    score, quality = score_group(title, about)
                    entry["title"] = title[:100]
                    if about:
                        entry["desc"] = about[:200]
                    entry["score"] = score
                    entry["quality"] = quality
                    entry["quality_at"] = datetime.now(timezone.utc).isoformat()
                    if isinstance(members, int) and members > 0:
                        entry["members"] = members
                        entry["members_at"] = datetime.now(timezone.utc).isoformat()
                    log.info("Scored %s: %s (%d/10) title=%s", group[:40], quality, score, (title or "?")[:40])
            state[group] = entry
            save_state(state)
            log.info("[%d/%d] %s -> %s (%s)", i + 1, len(todo), group, status, detail[:60])

            if status == "floodwait":
                try:
                    wait = int(detail) + random.randint(30, 90)
                except ValueError:
                    wait = 120
                log.warning("Flood wait %ds, sleeping...", wait)
                await asyncio.sleep(wait)
            elif i < len(todo) - 1:
                delay = random.randint(JOIN_DELAY_MIN, JOIN_DELAY_MAX)
                await asyncio.sleep(delay)

        joined = sum(1 for v in state.values() if v.get("status") in ("joined", "already"))
        q = {}
        for v in state.values():
            if isinstance(v, dict) and v.get("quality"):
                q[v["quality"]] = q.get(v["quality"], 0) + 1
        log.info("Done. State: %d joined/already of %d tracked; quality=%s", joined, len(state), q)
        return 0
    finally:
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
