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


def run_bot():
    log.info("[THREAD] Starting interactive bot...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    import bot_interactive
    try:
        bot_interactive.main()
    except Exception as e:
        log.error("[THREAD] Bot crashed: %s", e)


def run_referral_tracker():
    log.info("[THREAD] Starting referral tracker...")
    sys.argv = [sys.argv[0]]
    from referral_tracker import event_listener
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(event_listener())
    except Exception as e:
        log.error("[THREAD] Referral tracker crashed: %s", e)


def run_group_post():
    log.info("[TASK] Starting group cross-post...")
    result = subprocess.run(
        [sys.executable, "group_poster.py"],
        capture_output=True, text=True, timeout=600
    )
    if result.returncode == 0:
        log.info("[TASK] Group post success: %s", result.stdout.strip()[-200:])
    else:
        log.error("[TASK] Group post failed: %s", result.stderr.strip()[-300:])


def run_promo():
    log.info("[TASK] Starting promo sender...")
    result = subprocess.run(
        [sys.executable, "promo_sender.py"],
        capture_output=True, text=True, timeout=1800
    )
    if result.returncode == 0:
        log.info("[TASK] Promo sender success: %s", result.stdout.strip()[-200:])
    else:
        log.error("[TASK] Promo sender failed: %s", result.stderr.strip()[-300:])


def run_daily_report():
    log.info("[TASK] Starting daily report...")
    result = subprocess.run(
        [sys.executable, "daily_report.py"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        log.info("[TASK] Daily report success")
    else:
        log.error("[TASK] Daily report failed: %s", result.stderr.strip()[-300:])


async def periodic_tasks():
    log.info("Periodic task loop started")

    while True:
        if should_run("group_post", 2):
            log.info("--- Group post due ---")
            mark_run("group_post")
            try:
                run_group_post()
            except Exception as e:
                log.error("Group post error: %s", e)

        if should_run("promo_run", 6):
            log.info("--- Promo sender due ---")
            mark_run("promo_run")
            try:
                run_promo()
            except Exception as e:
                log.error("Promo error: %s", e)

        if should_run("daily_report", 24):
            log.info("--- Daily report due ---")
            mark_run("daily_report")
            try:
                run_daily_report()
            except Exception as e:
                log.error("Report error: %s", e)

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
