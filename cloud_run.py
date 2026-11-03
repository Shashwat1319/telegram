#!/usr/bin/env python3
"""Cloud runner — affiliate marketing tasks without laptop.

Runs channel posting, group posting, site rebuild, and daily report via GitHub
Actions.  Telethon session is loaded from the TELEGRAM_SESSION_1 secret
(StringSession format) so no .session file is needed.

Usage:
  python cloud_run.py                    # run all due tasks
  python cloud_run.py --task channel     # run only channel posting
  python cloud_run.py --task group       # run only group posting
  python cloud_run.py --task site        # run only site rebuild
  python cloud_run.py --task report      # run only daily report
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# ── logging ──────────────────────────────────────────────────────────────────
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("cloud_run")

# ── env ──────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@smartgahr")
TELEGRAM_SESSION_1 = os.getenv("TELEGRAM_SESSION_1", "")
API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "https://smartgahr.netlify.app")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
MASTER_PLAN = "MASTER_PLAN.md"  # never commit this

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# ── config ───────────────────────────────────────────────────────────────────
sys.path.insert(0, ROOT)
from config_loader import load_config

CONFIG = load_config()
STATE_FILE = "cloud_state.json"


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _should_run(state, task, interval_hours):
    last = state.get(task)
    if not last:
        return True
    try:
        dt = datetime.fromisoformat(last)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
        return elapsed >= interval_hours * 3600
    except Exception:
        return True


def _mark_run(state, task):
    state[task] = datetime.now(timezone.utc).isoformat()
    save_state(state)


# ── tasks ─────────────────────────────────────────────────────────────────────

def run_channel_post():
    """Post 1 deal to Telegram channel (from content_home.json / content_bdia.json)."""
    try:
        from poster import post_next_deal
        log.info("[CHANNEL] Running channel post...")
        # post_next_deal calls asyncio.run(post_content()) internally
        post_next_deal()
        log.info("[CHANNEL] Done.")
    except Exception as e:
        log.error("[CHANNEL] Failed: %s", e)


def run_group_post():
    """Post to Telegram groups (2 rounds/day, 7h gap)."""
    try:
        import asyncio
        from group_poster import main as group_post_main
        log.info("[GROUP] Running group post...")
        asyncio.run(asyncio.wait_for(group_post_main(), timeout=8900))
        log.info("[GROUP] Done.")
    except Exception as e:
        log.error("[GROUP] Failed: %s", e)


def run_site_rebuild():
    """Rebuild static deal pages and push to GitHub (Netlify auto-deploys)."""
    import subprocess
    log.info("[SITE] Rebuilding site...")
    try:
        r = subprocess.run(
            [sys.executable, "_site_builder.py"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        last = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        log.info("[SITE] builder: %s", last[-1] if last else "(no output)")
        if r.returncode != 0:
            log.error("[SITE] builder exited %s", r.returncode)
            return
        # Stage only generated site files
        site_paths = [
            "netlify-redirector/index.html",
            "netlify-redirector/deals/index.html",
            "netlify-redirector/sitemap.xml",
        ]
        subprocess.run(["git", "add"] + site_paths, check=True, capture_output=True, timeout=60)
        chk = subprocess.run(["git", "diff", "--cached", "--quiet"], timeout=60)
        if chk.returncode == 0:
            log.info("[SITE] no changes — skip commit")
            return
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        subprocess.run(
            ["git", "commit", "-m", "site: daily deals update %s" % stamp],
            check=True, capture_output=True, timeout=60,
        )
        p = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        )
        if p.returncode != 0:
            log.error("[SITE] push failed: %s", ((p.stderr or "").strip())[-200:])
        else:
            log.info("[SITE] pushed — Netlify auto-deploy triggered")
    except Exception as e:
        log.error("[SITE] failed: %s", e)


def run_daily_report():
    """Generate and send the daily report to the admin chat."""
    try:
        import asyncio
        from reporting import daily_report
        log.info("[REPORT] Generating daily report...")
        asyncio.run(daily_report())
        log.info("[REPORT] Done.")
    except Exception as e:
        log.error("[REPORT] Failed: %s", e)


def runPinterest():
    """Run Pinterest cloud drip (2 pins/day)."""
    # Already handled by pinterest_pins.yml — do nothing here
    log.info("[PINTEREST] handled by separate workflow")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cloud runner for affiliate tasks")
    parser.add_argument("--task", choices=["channel", "group", "site", "report", "all"],
                        default="all", help="Which task to run (default: all)")
    args = parser.parse_args()

    # Load Telethon session from env (StringSession)
    if TELEGRAM_SESSION_1:
        try:
            from telethon.sessions import StringSession
            os.environ.setdefault("TELEGRAM_SESSION_STRING", TELEGRAM_SESSION_1)
            log.info("Telethon session loaded from env")
        except Exception as e:
            log.warning("Telethon session load failed: %s", e)
    else:
        log.warning("TELEGRAM_SESSION_1 not set — group posting may fail")

    state = load_state()

    if args.task == "all" or args.task == "channel":
        if _should_run(state, "channel_post", 2):  # every 2 hours
            run_channel_post()
            _mark_run(state, "channel_post")
        else:
            log.info("[CHANNEL] Skipped (interval not reached)")

    if args.task == "all" or args.task == "group":
        if _should_run(state, "group_post", 4):  # every 4 hours
            run_group_post()
            _mark_run(state, "group_post")
        else:
            log.info("[GROUP] Skipped (interval not reached)")

    if args.task == "all" or args.task == "site":
        if _should_run(state, "site_rebuild", 24):  # daily
            run_site_rebuild()
            _mark_run(state, "site_rebuild")
        else:
            log.info("[SITE] Skipped (interval not reached)")

    if args.task == "all" or args.task == "report":
        # Daily report: run if it's been >20 hours since last report and it's
        # roughly morning in IST (03:00-06:00 UTC = 08:30-11:30 IST).
        now_utc = datetime.now(timezone.utc)
        if 3 <= now_utc.hour <= 6:
            if _should_run(state, "daily_report", 20):
                run_daily_report()
                _mark_run(state, "daily_report")
            else:
                log.info("[REPORT] Skipped (already sent today)")
        else:
            log.info("[REPORT] Not morning IST yet — skipping")

    log.info("Cloud run complete.")


if __name__ == "__main__":
    main()
