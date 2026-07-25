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


def acquire_pid_lock():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if sys.platform != "win32":
                try:
                    os.kill(old_pid, 0)
                    log.error("Another orchestrator instance is running (PID: %d). Exiting.", old_pid)
                    return False
                except (ProcessLookupError, SystemError):
                    log.warning("Stale PID file found (PID %d is dead). Overwriting.", old_pid)
                except OSError:
                    pass
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
        return True


def mark_run(task_name):
    STATE[f"last_{task_name}"] = datetime.now(timezone.utc).isoformat()
    save_state()


def run_bot_thread():
    log.info("[THREAD] Starting Telegram Bot...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from bot import run_bot
        run_bot()
    except Exception as e:
        log.error("[THREAD] Bot error: %s", e)
        log.warning("Bot daemon will respawn in 30s...")
        _shutdown.wait(timeout=30)
        if not _shutdown.is_set():
            run_bot_thread()


def run_referral_thread():
    log.info("[THREAD] Starting Referral Tracker...")
    try:
        from referral import event_listener
        asyncio.run(event_listener())
    except Exception as e:
        log.error("[THREAD] Referral tracker error: %s", e)
        log.warning("Referral tracker will respawn in 30s...")
        _shutdown.wait(timeout=30)
        if not _shutdown.is_set():
            run_referral_thread()


def run_task_safely(func, task_name):
    try:
        log.info("[TASK] Executing %s...", task_name)
        func()
        mark_run(task_name)
        log.info("[TASK] %s completed successfully.", task_name)
    except Exception as e:
        log.error("[TASK] %s failed: %s", task_name, e)


def task_product_feed():
    try:
        from feeder import feed
        feed(limit=50)
    except ImportError as e:
        log.error("[FEED] feeder module missing or broken: %s", e)


def task_channel_post():
    from poster import post_next_deal
    post_next_deal()


def task_group_post():
    from group_poster import main as group_post_main
    asyncio.run(group_post_main())


def task_daily_report():
    from reporting import daily_report
    asyncio.run(daily_report())


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
    bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
    ref_thread = threading.Thread(target=run_referral_thread, daemon=True)
    bot_thread.start()
    ref_thread.start()

    log.info("Orchestrator running. Press Ctrl+C to stop.")

    try:
        while not _shutdown.is_set():
            config = load_config()
            tasks_cfg = config.get("tasks", {})

            if tasks_cfg.get("product_feed", {}).get("enabled", True):
                hours = tasks_cfg.get("product_feed", {}).get("interval_hours", 12)
                if should_run("product_feed", hours):
                    run_task_safely(task_product_feed, "product_feed")

            if tasks_cfg.get("channel_posting", {}).get("enabled", True):
                hours = tasks_cfg.get("channel_posting", {}).get("interval_hours", 0.5)
                if should_run("channel_post", hours):
                    run_task_safely(task_channel_post, "channel_post")

            if tasks_cfg.get("group_posting", {}).get("enabled", False):
                hours = tasks_cfg.get("group_posting", {}).get("interval_hours", 2)
                if should_run("group_post", hours):
                    run_task_safely(task_group_post, "group_post")

            if tasks_cfg.get("daily_report", {}).get("enabled", True):
                hours = tasks_cfg.get("daily_report", {}).get("interval_hours", 24)
                if should_run("daily_report", hours):
                    run_task_safely(task_daily_report, "daily_report")

            _shutdown.wait(timeout=60)

    finally:
        save_state()
        release_pid_lock()
        log.info("Orchestrator clean exit.")


if __name__ == "__main__":
    main()