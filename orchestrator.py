import os, sys, json, time, random, logging, asyncio, threading, subprocess
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = "orchestrator.log"
STATE_FILE = "orchestrator_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("orchestrator")

STATE = {
    "last_group_post": None,
    "last_promo_run": None,
    "last_daily_report": None,
    "last_referral_reminder": None,
    "started_at": datetime.now(timezone.utc).isoformat(),
}

_thread_health = {"bot": True, "referral": True}
_thread_lock = threading.Lock()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_dt(s):
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def load_state():
    global STATE
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                STATE.update(json.load(f))
            log.info("State loaded: %s", STATE_FILE)
        except Exception as e:
            log.warning("Could not load state: %s", e)


def save_state():
    STATE["last_updated"] = utcnow().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(STATE, f, indent=2)


def should_run(task_name, interval_hours):
    last_key = f"last_{task_name}"
    last_run = STATE.get(last_key)
    if not last_run:
        return True
    elapsed = (utcnow() - parse_dt(last_run)).total_seconds()
    return elapsed >= interval_hours * 3600


def mark_run(task_name):
    STATE[f"last_{task_name}"] = utcnow().isoformat()
    save_state()


def set_thread_health(name, healthy):
    with _thread_lock:
        _thread_health[name] = healthy


def check_thread_health():
    with _thread_lock:
        return _thread_health.copy()


def run_subprocess_safe(cmd, timeout, task_name):
    """Run subprocess with proper timeout handling and logging."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            log.info("[TASK] %s success: %s", task_name, result.stdout.strip()[-200:])
        else:
            log.error("[TASK] %s failed (code %d): %s", task_name, result.returncode, result.stderr.strip()[-300:])
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log.error("[TASK] %s timed out after %ds", task_name, timeout)
        return False
    except Exception as e:
        log.error("[TASK] %s exception: %s", task_name, e)
        return False


def run_bot():
    log.info("[THREAD] Starting interactive bot...")
    while True:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            import bot_interactive
            bot_interactive.main()
        except Exception as e:
            log.error("[THREAD] Bot crashed: %s", e)
            set_thread_health("bot", False)
        log.info("[THREAD] Bot thread restarting in 10s...")
        set_thread_health("bot", True)
        time.sleep(10)


def run_referral_tracker():
    log.info("[THREAD] Starting referral tracker...")
    while True:
        try:
            sys.argv = [sys.argv[0]]
            from referral_tracker import event_listener
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(event_listener())
        except Exception as e:
            log.error("[THREAD] Referral tracker crashed: %s", e)
            set_thread_health("referral", False)
        log.info("[THREAD] Referral tracker restarting in 10s...")
        set_thread_health("referral", True)
        time.sleep(10)


def run_group_post():
    log.info("[TASK] Starting group cross-post...")
    run_subprocess_safe([sys.executable, "group_poster.py"], 600, "group_post")
    mark_run("group_post")


def run_promo():
    log.info("[TASK] Starting promo sender...")
    run_subprocess_safe([sys.executable, "promo_sender.py"], 1800, "promo_run")
    mark_run("promo_run")


def run_daily_report():
    log.info("[TASK] Starting daily report...")
    run_subprocess_safe([sys.executable, "daily_report.py"], 60, "daily_report")
    mark_run("daily_report")


async def periodic_tasks():
    log.info("Periodic task loop started")

    while True:
        try:
            if should_run("group_post", 2):
                log.info("--- Group post due ---")
                run_group_post()

            if should_run("promo_run", 6):
                log.info("--- Promo sender due ---")
                run_promo()

            if should_run("daily_report", 24):
                log.info("--- Daily report due ---")
                run_daily_report()

            # Health check
            health = check_thread_health()
            for name, healthy in health.items():
                if not healthy:
                    log.warning("[HEALTH] Thread %s is unhealthy!", name)

        except Exception as e:
            log.error("Periodic loop error: %s", e)

        next_check = utcnow() + timedelta(minutes=30)
        log.info("Next periodic check at %s", next_check.strftime("%H:%M"))
        await asyncio.sleep(1800)


def main():
    load_state()

    pid = os.getpid()
    log.info("=" * 50)
    log.info("ORCHESTRATOR STARTED (PID: %d)", pid)
    log.info("=" * 50)

    threads = []

    bot_thread = threading.Thread(target=run_bot, name="bot", daemon=True)
    threads.append(bot_thread)
    bot_thread.start()
    log.info("[MAIN] Bot thread started")

    ref_thread = threading.Thread(target=run_referral_tracker, name="referral", daemon=True)
    threads.append(ref_thread)
    ref_thread.start()
    log.info("[MAIN] Referral tracker thread started")

    log.info("[MAIN] Starting periodic task loop...")
    try:
        asyncio.run(periodic_tasks())
    except KeyboardInterrupt:
        log.info("Shutting down...")
    except Exception as e:
        log.error("Periodic loop crashed: %s", e)
    finally:
        save_state()
        log.info("Orchestrator stopped. State saved.")


if __name__ == "__main__":
    main()