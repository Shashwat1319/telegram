import subprocess, time, os, sys
from datetime import datetime

POST = 900       # 15 min
SYNC = 3600      # 1 hr
CONTENT = 7200   # 2 hrs
FB = 14400       # 4 hrs
REPORT = 43200   # 12 hrs
SLEEP = 300

def run(name, timeout=300):
    t = datetime.now().strftime('%H:%M:%S')
    print(f"\n[{t}] {name}")
    try:
        r = subprocess.run([sys.executable] + name.split(), timeout=timeout)
        return r.returncode == 0
    except: return False

def main():
    print(f"=== Orchestrator @ {datetime.now()} ===")
    lp = ls = lc = lf = lr = 0
    while True:
        n = time.time()
        if n - ls > SYNC and run("trending_updater.py", 120): ls = n
        if n - lp > POST and run("bot_post.py --dry-run", 60): lp = n
        if n - lc > CONTENT and run("auto_blogger.py", 120): lc = n
        if n - lf > FB and run("fb_bot_post.py", 30): lf = n
        if n - lr > REPORT and run("daily_report.py", 30): lr = n
        time.sleep(SLEEP)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nStopped.")
    except Exception as e: print(f"\nFatal: {e}")
