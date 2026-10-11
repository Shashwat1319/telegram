"""Auto-join promo groups so the user account can post deals in them.

Reads @usernames AND t.me/+ invite links from verified_promo_groups.txt and
discovered_groups.txt, joins each public group/channel with a random pace
(anti-flood), records status per entry, and optionally probes whether we have
send rights (so group_poster only targets writable chats). Entries marked
send=blocked (kicked earlier) are re-attempted.

Usage:
    py join_promo_groups.py            # join everything not yet joined + re-kicked
    py join_promo_groups.py --probe    # also probe send rights after joining
    py join_promo_groups.py --limit 10 # join at most 10 new entries
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

INVITE_RE = re.compile(r"(?:https?://)?t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]+)")


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
    """Join a public chat by username or invite link. Returns (status, detail)."""
    m = INVITE_RE.search(username)
    if m:
        try:
            await asyncio.wait_for(client(ImportChatInviteRequest(m.group(1))), timeout=30)
        except UserAlreadyParticipantError:
            return "already", "member"
        except FloodWaitError as e:
            return "floodwait", str(e.seconds)
        except Exception as e:
            return "error", f"{type(e).__name__}: {e}"
        return "joined", "invite link"
    try:
        entity = await asyncio.wait_for(client.get_entity(username), timeout=30)
        try:
            await asyncio.wait_for(client(JoinChannelRequest(entity)), timeout=30)
        except UserAlreadyParticipantError:
            return "already", "member"
        except FloodWaitError as e:
            return "floodwait", str(e.seconds)
        return "joined", getattr(entity, "title", username)
    except UsernameNotOccupiedError:
        return "not_found", "username does not exist"
    except ChannelPrivateError:
        return "private", "invite only"
    except FloodWaitError as e:
        return "floodwait", str(e.seconds)
    except Exception as e:
        return "error", f"{type(e).__name__}: {e}"


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
    """Retry failed joins only after 7 days; floodwait always retries; kicked (send=blocked) retried via caller."""
    if not entry:
        return True
    if entry.get("status") == "floodwait":
        return True
    if entry.get("status") in ("joined", "already"):
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
            status, detail = await join_one(client, group)
            old = state.get(group) or {}
            entry = {
                "status": status,
                "detail": detail[:120],
                "at": datetime.now(timezone.utc).isoformat(),
            }
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
        log.info("Done. State: %d joined/already of %d tracked", joined, len(state))
        return 0
    finally:
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
