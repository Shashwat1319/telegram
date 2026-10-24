"""Discover new promo-group invite links shared inside chats we're already in.

Scans recent messages of every group/channel the account belongs to for
t.me/+ and t.me/joinchat invite links, dedupes against verified_promo_groups.txt
and its own output, and appends new links to discovered_groups.txt (gitignored).
join_promo_groups.py reads that file and joins them.

2026-10-24: provenance (which chat + snippet a link came from) is written to
discovered_groups_meta.json so junk sources can be identified later. Cap
raised 50 -> 100 new links/run (scans are read-only; joining stays capped
separately at content.group_joins_per_day).

Usage:
    py discover_groups.py                # scan last 60 messages per dialog
    py discover_groups.py --limit 200    # deeper scan
    py discover_groups.py --max-new 30   # override per-run cap
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("discover")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_1")

VERIFIED_FILE = "verified_promo_groups.txt"
DISCOVERED_FILE = "discovered_groups.txt"
META_FILE = "discovered_groups_meta.json"

INVITE_RE = re.compile(r"(?:https?://)?t\.me/(\+|joinchat/)([A-Za-z0-9_-]+)")
MAX_NEW_PER_RUN = 100
DIALOG_PAUSE_S = 1.5


def _load_links(path):
    out = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    out.add(line)
    return out


def _normalize(link):
    """Canonical form so dedupe works across prefix variants."""
    m = INVITE_RE.search(link)
    if not m:
        return link
    return f"https://t.me/{m.group(1)}{m.group(2)}"


async def main():
    if not API_ID or not API_HASH or not SESSION_STR:
        log.error("API_ID/API_HASH/TELEGRAM_SESSION_1 missing")
        return 1

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60, help="messages to scan per dialog")
    ap.add_argument("--max-new", type=int, default=MAX_NEW_PER_RUN, help="max new links this run")
    args = ap.parse_args()
    max_new = max(1, args.max_new)

    known = {_normalize(x) for x in (_load_links(VERIFIED_FILE) | _load_links(DISCOVERED_FILE))}
    log.info("Known invite links/usernames: %d", len(known))

    client = TelegramClient(StringSession(SESSION_STR), int(API_ID), API_HASH, timeout=30)
    await asyncio.wait_for(client.connect(), timeout=45)
    new_links = {}
    try:
        if not await client.is_user_authorized():
            log.error("Session not authorized")
            return 1

        dialogs = await client.get_dialogs()
        log.info("Scanning %d dialogs (last %d msgs each)...", len(dialogs), args.limit)

        for idx, d in enumerate(dialogs, 1):
            if not (d.is_group or d.is_channel):
                continue
            title = getattr(d.entity, "title", str(d.id))
            try:
                async for msg in client.iter_messages(d.entity, limit=args.limit):
                    text = msg.raw_text or msg.text or ""
                    if not text or "t.me/" not in text:
                        continue
                    for m in INVITE_RE.finditer(text):
                        link = f"https://t.me/{m.group(1)}{m.group(2)}"
                        nlink = _normalize(link)
                        if nlink in known or nlink in new_links:
                            continue
                        new_links[nlink] = {
                            "src": title,
                            "snippet": text[:200],
                            "seen_at": datetime.now(timezone.utc).isoformat(),
                        }
                        log.info("NEW invite: %s  (from %s)", link, title[:40])
                        if len(new_links) >= max_new:
                            break
                    if len(new_links) >= max_new:
                        break
            except FloodWaitError as e:
                wait = e.seconds + 30
                log.warning("FloodWait %ds while scanning — sleeping", wait)
                await asyncio.sleep(wait)
            except Exception as e:
                log.warning("Scan failed for %s: %s", title[:40], e)
            if len(new_links) >= max_new:
                log.info("Reached cap of %d new links this run", max_new)
                break
            await asyncio.sleep(DIALOG_PAUSE_S)
            if idx % 10 == 0:
                log.info("Progress: %d/%d dialogs, %d new links", idx, len(dialogs), len(new_links))

        if new_links:
            created = not os.path.exists(DISCOVERED_FILE)
            with open(DISCOVERED_FILE, "a", encoding="utf-8") as f:
                if created:
                    f.write(f"# Discovered {datetime.now(timezone.utc).isoformat()}\n")
                for link in new_links:
                    f.write(f"{link}\n")
            # Provenance sidecar — join/group_poster keep reading the plain .txt.
            try:
                meta = {}
                if os.path.exists(META_FILE):
                    with open(META_FILE, encoding="utf-8") as f:
                        meta = json.load(f)
                        if not isinstance(meta, dict):
                            meta = {}
                meta.update(new_links)
                tmp = META_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
                os.replace(tmp, META_FILE)
            except Exception as e:
                log.warning("Could not write %s: %s", META_FILE, e)
            log.info("Wrote %d new invite links to %s (+meta)", len(new_links), DISCOVERED_FILE)
        else:
            log.info("No new invite links found")
        return 0
    finally:
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
