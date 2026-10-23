import os
import sys
import time
import logging
import asyncio
import threading
import signal
from datetime import datetime, timezone
from dotenv import load_dotenv

from config_loader import load_config
from data import load_json, save_json

load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("orchestrator.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("orchestrator")

_shutdown = threading.Event()
PID_FILE = "orchestrator.pid"
STATE_FILE = "orchestrator_state.json"

STATE = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "last_product_feed": None,
    "last_channel_post": None,
    "last_group_post": None,
    "last_daily_report": None,
}


def _pid_alive(pid):
    """True if another process with this PID is running.
    On Windows os.kill(pid, 0) TERMINATES the target — must use OpenProcess."""
    if pid <= 0:
        return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, SystemError):
            return False
        except OSError:
            return True  # exists but not ours — assume alive (safe)
    try:
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def acquire_pid_lock():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if old_pid != os.getpid() and _pid_alive(old_pid):
                log.error("Another orchestrator instance is running (PID: %d). Exiting.", old_pid)
                return False
            if old_pid != os.getpid():
                log.warning("Stale PID file found (PID %d is dead). Overwriting.", old_pid)
        except (ValueError, OSError):
            pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_pid_lock():
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


def load_state():
    global STATE
    loaded = load_json(STATE_FILE, default=None)
    if loaded:
        STATE.update(loaded)


def save_state():
    STATE["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_json(STATE_FILE, STATE)


def should_run(task_name, interval_hours):
    last_key = f"last_{task_name}"
    last_run = STATE.get(last_key)
    if not last_run:
        return True
    try:
        dt = datetime.fromisoformat(last_run)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
        return elapsed >= interval_hours * 3600
    except Exception:
        return True  # corrupt timestamp — run instead of starving the task forever


def mark_run(task_name):
    STATE[f"last_{task_name}"] = datetime.now(timezone.utc).isoformat()
    save_state()


def run_bot_thread():
    while not _shutdown.is_set():
        log.info("[THREAD] Starting Telegram Bot...")
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            from bot import run_bot
            run_bot()
            break
        except Exception as e:
            log.error("[THREAD] Bot error: %s", e)
            if _shutdown.is_set():
                break
            log.warning("Bot daemon will respawn in 30s...")
            _shutdown.wait(timeout=30)
        finally:
            if loop and not loop.is_closed():
                loop.close()


def run_referral_thread():
    retry_count = 0
    while not _shutdown.is_set():
        log.info("[THREAD] Starting Referral Tracker...")
        try:
            from referral import event_listener
            asyncio.run(event_listener())
            retry_count = 0  # Reset on successful run (disconnected cleanly)
            break
        except Exception as e:
            log.error("[THREAD] Referral tracker error: %s", e)
            if _shutdown.is_set():
                break
            retry_count += 1
            backoff = min(30 * (2 ** min(retry_count - 1, 4)), 300)  # 30, 60, 120, 240, 300s max
            log.warning("Referral tracker will respawn in %ds (attempt %d)...", backoff, retry_count)
            _shutdown.wait(timeout=backoff)


def run_member_poller_thread():
    """Fallback member count poller — catches joins that event listener misses."""
    while not _shutdown.is_set():
        log.info("[THREAD] Starting Member Count Poller...")
        try:
            from referral import member_count_poller
            asyncio.run(member_count_poller(interval_minutes=30))
            break
        except Exception as e:
            log.error("[THREAD] Member poller error: %s", e)
            if _shutdown.is_set():
                break
            log.warning("Member poller will respawn in 60s...")
            _shutdown.wait(timeout=60)


def run_task_safely(func, task_name):
    try:
        log.info("[TASK] Executing %s...", task_name)
        func()
        log.info("[TASK] %s completed successfully.", task_name)
    except SystemExit as e:
        log.error("[TASK] %s aborted (SystemExit=%s) — module hard-exited (missing env/deps?)", task_name, e.code)
    except TimeoutError:
        log.error("[TASK] %s hit its hard timeout — will retry next interval", task_name)
    except Exception as e:
        log.error("[TASK] %s failed: %s", task_name, e)
    finally:
        # Mark even on failure so a broken task doesn't retry every 60s tick
        mark_run(task_name)


def task_product_feed():
    try:
        from feeder import feed
        feed(limit=50)
        try:
            from config_loader import load_config
            ht_cfg = load_config().get("content", {}).get("high_ticket", {})
            if ht_cfg.get("enabled", False):
                feed(limit=50, ht=True,
                     source=ht_cfg.get("source_file", "product.json"),
                     output=ht_cfg.get("file", "content_ht.json"))
        except Exception as e:
            log.error("[FEED] HT feed failed: %s", e)
    except ImportError as e:
        log.error("[FEED] feeder module missing or broken: %s", e)


def task_channel_post():
    from poster import post_next_deal
    post_next_deal()


def task_group_post():
    from group_poster import main as group_post_main
    async def _run():
        # 2.5h hard cap: worst case is 12 groups x (600s max delay + ~30s send) = ~126 min;
        # the old 90-min cap killed runs mid-cycle (e.g. 2026-10-12 18:39 run).
        await asyncio.wait_for(group_post_main(), timeout=9000)
    asyncio.run(_run())


def task_daily_report():
    from reporting import daily_report
    asyncio.run(daily_report())


def task_goal_check():
    from reporting import check_goal
    asyncio.run(check_goal())


def task_promo_post():
    """Daily share-bait/value post (promo_daily templates) — views engine.
    Idempotent via promo_state last_date; hour gate pins to IST daytime."""
    try:
        from zoneinfo import ZoneInfo
        hour = datetime.now(ZoneInfo("Asia/Kolkata")).hour
        if not (11 <= hour <= 21):
            return
        from promo_daily import generate_post
        post = generate_post()
        if not post:
            return
        asyncio.run(_send_promo_to_channel(post))
    except ImportError as e:
        log.error("[PROMO] module missing or broken: %s", e)


async def _send_promo_to_channel(text):
    from telegram import Bot
    from telegram.error import TelegramError
    token = os.getenv("BOT_TOKEN")
    chat = load_config().get("bot", {}).get("channel_id") or load_config().get("bot", {}).get("channel_handle")
    if not token or not chat:
        log.error("[PROMO] BOT_TOKEN/channel missing in env/config")
        return
    async with Bot(token=token) as bot:
        try:
            await bot.send_message(chat_id=chat, text=text, parse_mode="Markdown",
                                   disable_web_page_preview=True)
        except TelegramError as e:
            log.warning("[PROMO] Markdown send failed (%s) — retrying plain", e)
            try:
                await bot.send_message(chat_id=chat, text=text, disable_web_page_preview=True)
            except Exception as e2:
                log.error("[PROMO] send failed: %s", e2)
                return
    log.info("[PROMO] posted to %s", chat)


def _run_script(script, args=None, timeout=1800):
    """Run a sibling script in a subprocess (console-less safe: pipes only).
    Safety limits (4/day combined budget, FloodWait abort, DM pacing) live
    inside member_dm/swap_dm themselves — subprocess just triggers them."""
    import subprocess
    cmd = [sys.executable, script] + list(args or [])
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-4:]
    for line in tail:
        log.info("[SCRIPT] %s: %s", script, line)
    if r.returncode != 0:
        log.error("[SCRIPT] %s exited with code %s", script, r.returncode)


def _ist_now():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Kolkata"))


def task_swap_dm():
    """Daily swap-pitch DMs, 19-21 IST. Idempotent: skips if any swap sent
    today (respects the 4/day combined DM budget with member_dm)."""
    if not (19 <= _ist_now().hour <= 21):
        return
    today = _ist_now().date().isoformat()
    state = load_json("swap_dm_state.json", {}) or {}
    sent_today = any(
        isinstance(v, dict) and v.get("status") == "sent"
        and str(v.get("at", ""))[:10] == today
        for v in state.values()
    )
    if sent_today:
        return
    _run_script("swap_dm.py", ["--limit", "2"])


def task_member_dm():
    """Daily member DMs, 20-21 IST (after swap). member_dm self-clamps to the
    remaining combined 4/day budget, so double-runs are safe."""
    if not (20 <= _ist_now().hour <= 21):
        return
    _run_script("member_dm.py", [])


def task_member_scrape():
    """Weekly pool refresh (member_scrape self-throttles: skips groups
    rescraped within 7 days). Gate keeps the daily tick cheap."""
    if not (5 <= _ist_now().hour <= 7):
        return
    _run_script("member_scrape.py", [])


def keep_awake():
    """Prevent OS sleep while the orchestrator runs.
    2026-10-13: machine slept 09:06-15:40 IST (zero log lines, all tasks fired
    overdue at 16:42) — cost the entire 11:00-14:00 prime window."""
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        r = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        if r:
            log.info("[AWAKE] OS sleep disabled while orchestrator runs")
        else:
            log.warning("[AWAKE] SetThreadExecutionState returned 0 (no effect)")
    except Exception as e:
        log.warning("[AWAKE] could not set execution state: %s", e)


def main():
    if not acquire_pid_lock():
        sys.exit(1)

    load_state()

    def handle_signal(sig, frame):
        log.info("Shutdown signal received (%s). Stopping...", sig)
        _shutdown.set()

    signal.signal(signal.SIGINT, handle_signal)
    try:
        signal.signal(signal.SIGTERM, handle_signal)
    except AttributeError:
        pass  # SIGTERM not available on Windows

    # Start background bot & referral threads
    tasks0 = load_config().get("tasks", {})
    referral_on = tasks0.get("referral_tracker", {}).get("enabled", True)
    bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
    ref_thread = threading.Thread(target=run_referral_thread, daemon=True) if referral_on else None
    poller_thread = threading.Thread(target=run_member_poller_thread, daemon=True) if referral_on else None
    bot_thread.start()
    if ref_thread:
        ref_thread.start()
    if poller_thread:
        poller_thread.start()

    log.info("Orchestrator running. Press Ctrl+C to stop.")
    keep_awake()

    last_hb = time.time()
    try:
        while not _shutdown.is_set():
            if not bot_thread.is_alive():
                log.warning("Bot thread died — restarting...")
                bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
                bot_thread.start()
            if ref_thread is not None and not ref_thread.is_alive():
                log.warning("Referral thread died — restarting...")
                ref_thread = threading.Thread(target=run_referral_thread, daemon=True)
                ref_thread.start()
            if poller_thread is not None and not poller_thread.is_alive():
                log.warning("Member poller thread died — restarting...")
                poller_thread = threading.Thread(target=run_member_poller_thread, daemon=True)
                poller_thread.start()

            config = load_config()
            tasks_cfg = config.get("tasks", {})

            if tasks_cfg.get("channel_posting", {}).get("enabled", True):
                hours = tasks_cfg.get("channel_posting", {}).get("interval_hours", 0.5)
                if should_run("channel_post", hours):
                    run_task_safely(task_channel_post, "channel_post")

            if tasks_cfg.get("product_feed", {}).get("enabled", True):
                hours = tasks_cfg.get("product_feed", {}).get("interval_hours", 12)
                if should_run("product_feed", hours):
                    run_task_safely(task_product_feed, "product_feed")

            if tasks_cfg.get("group_posting", {}).get("enabled", False):
                hours = tasks_cfg.get("group_posting", {}).get("interval_hours", 2)
                if should_run("group_post", hours):
                    run_task_safely(task_group_post, "group_post")

            if tasks_cfg.get("daily_report", {}).get("enabled", True):
                hours = tasks_cfg.get("daily_report", {}).get("interval_hours", 24)
                if should_run("daily_report", hours):
                    run_task_safely(task_daily_report, "daily_report")

            if tasks_cfg.get("goal_tracker", {}).get("enabled", True):
                hours = tasks_cfg.get("goal_tracker", {}).get("interval_hours", 6)
                if should_run("goal_check", hours):
                    run_task_safely(task_goal_check, "goal_check")

            if tasks_cfg.get("promo_post", {}).get("enabled", True):
                hours = tasks_cfg.get("promo_post", {}).get("interval_hours", 1)
                if should_run("promo_post", hours):
                    run_task_safely(task_promo_post, "promo_post")

            if tasks_cfg.get("member_scrape", {}).get("enabled", True):
                hours = tasks_cfg.get("member_scrape", {}).get("interval_hours", 24)
                if should_run("member_scrape", hours):
                    run_task_safely(task_member_scrape, "member_scrape")

            if tasks_cfg.get("swap_dm", {}).get("enabled", True):
                hours = tasks_cfg.get("swap_dm", {}).get("interval_hours", 1)
                if should_run("swap_dm", hours):
                    run_task_safely(task_swap_dm, "swap_dm")

            if tasks_cfg.get("member_dm", {}).get("enabled", True):
                hours = tasks_cfg.get("member_dm", {}).get("interval_hours", 1)
                if should_run("member_dm", hours):
                    run_task_safely(task_member_dm, "member_dm")

            if time.time() - last_hb >= 1800:
                log.info("[HB] main loop alive (30 min heartbeat)")
                last_hb = time.time()

            _shutdown.wait(timeout=60)

    finally:
        save_state()
        release_pid_lock()
        log.info("Orchestrator clean exit.")


if __name__ == "__main__":
    main()