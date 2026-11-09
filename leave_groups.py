"""Leave junk Telegram groups (phalatu cleanup).

Targets ONLY groups that are proven worthless:
  1. paused by group_roi   -> 12-23 posts, 0 clicks (dead audience)
  2. send == "blocked"     -> we cannot post there anyway

Clickers, 0-post (untested) groups and writable active groups are NEVER touched.

Usage:
    py leave_groups.py            # dry run: list targets
    py leave_groups.py --apply    # actually leave + mark status=left
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("leave_groups")

STATE_FILE = "joined_groups_state.json"


def load_state():
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def targets(state):
    """Groups safe to leave: paused (0 clicks after N posts) or unpostable (blocked)."""
    out = []
    for g, e in state.items():
        if not isinstance(e, dict):
            continue
        if e.get("status") == "left":
            continue
        reason = None
        if e.get("paused"):
            reason = e.get("paused_reason") or "paused (0 clicks)"
        elif e.get("send") == "blocked":
            reason = "blocked (cannot post)"
        if reason:
            out.append((g, reason))
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually leave the groups")
    ap.add_argument("--delay", type=int, default=8, help="seconds between leaves (flood-safe)")
    args = ap.parse_args()

    state = load_state()
    tgts = targets(state)
    print(f"\n=== {len(tgts)} groups targeted for leaving ===")
    for g, reason in tgts:
        print(f"  {g[:45]:45s}  {reason}")

    if not args.apply:
        print("\n(dry run — use --apply to leave)")
        return 0

    from telethon import TelegramClient
    from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameNotOccupiedError
    from telethon.sessions import StringSession

    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    session = os.getenv("TELEGRAM_SESSION_1")
    if not (api_id and api_hash and session):
        log.error("API_ID/API_HASH/TELEGRAM_SESSION_1 missing")
        return 1

    import asyncio

    client = TelegramClient(StringSession(session), int(api_id), api_hash, timeout=30)
    await asyncio.wait_for(client.connect(), timeout=45)
    try:
        if not await client.is_user_authorized():
            log.error("Session not authorized")
            return 1

        left = failed = 0
        for g, reason in tgts:
            try:
                from telethon.tl.functions.channels import LeaveChannelRequest

                await client(LeaveChannelRequest(g))
                state[g]["status"] = "left"
                state[g]["left_at"] = datetime.now(timezone.utc).isoformat()
                state[g]["left_reason"] = reason
                left += 1
                print(f"[LEFT] {g[:45]}  ({reason})")
            except (ChannelPrivateError, UsernameNotOccupiedError) as e:
                # already gone / dead username -> mark left anyway, nothing to leave
                state[g]["status"] = "left"
                state[g]["left_at"] = datetime.now(timezone.utc).isoformat()
                state[g]["left_reason"] = f"gone: {type(e).__name__}"
                left += 1
                print(f"[GONE] {g[:45]}  ({type(e).__name__})")
            except FloodWaitError as e:
                log.warning("FloodWait %ss — stopping, will resume next run", e.seconds)
                break
            except Exception as e:
                failed += 1
                print(f"[FAIL] {g[:45]}  {type(e).__name__}: {e}")
            await asyncio.sleep(args.delay)

        save_state(state)
        print(f"\nDone. left={left} failed={failed}")
        log.info("Leave run complete: left=%d failed=%d", left, failed)
    finally:
        await client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
