import subprocess
import time
import os
import sys
from datetime import datetime

INTERVAL_FORWARD = 15 * 60      # 15 min (Growth Burst Mode - laptop IP safe)
INTERVAL_PROMO = 3 * 60 * 60    # 3 hours (Growth DM - laptop IP safe)
INTERVAL_REPORT = 12 * 60 * 60  # 12 hours (Daily Progress Report)

def start_background_task(script_name):
    print(f"[*] STARTING BACKGROUND TASK: {script_name}")
    try:
        return subprocess.Popen([sys.executable, script_name])
    except Exception as e:
        print(f"[CRITICAL] Could not start {script_name}: {e}")
        return None

def run_script(script_name, timeout=1800):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] RUNNING: {script_name}")
    try:
        result = subprocess.run(
            [sys.executable, script_name], 
            timeout=timeout,
            capture_output=False
        )
        print(f"[*] {script_name} finished (Exit Code: {result.returncode})")
    except subprocess.TimeoutExpired:
        print(f"[!] {script_name} timed out after {timeout}s")
    except Exception as e:
        print(f"[CRITICAL] Could not run {script_name}: {e}")

def git_sync():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Syncing with Cloud (GitHub)...")
    try:
        subprocess.run(["git", "add", "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Local tracker auto-sync"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, text=True)
        if "conflict" in result.stderr.lower() or result.returncode != 0:
            print("[!] Git conflict detected. Aborting rebase and forcing cloud state...")
            subprocess.run(["git", "rebase", "--abort"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "reset", "--hard", "origin/main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("[SUCCESS] Local repository is in sync with GitHub!")
    except Exception as e:
        print(f"[!] Error during git sync: {e}")

def main():
    print("="*50)
    print(" ARZI HYBRID ORCHESTRATOR v3.2 - LAPTOP MODE ")
    print("="*50)
    print("Cloud handles: Scraping, Member Growth, Referral Tracking, Trending Updates")
    print("Laptop handles: Forwarder (15min), Promo DMs (3hr), Reports (12hr)")
    print(f"Start Time: {datetime.now()}")
    
    last_forward = 0
    last_promo = 0
    last_report = 0

    print("[*] Starting AI Traffic Hijacker (Background)...")
    hijacker_process = start_background_task("traffic_hijacker.py")

    print("[*] Entering Hybrid Loop...")
    try:
        while True:
            git_sync()

            if hijacker_process and hijacker_process.poll() is not None:
                print("[!] AI Traffic Hijacker stopped. Restarting...")
                hijacker_process = start_background_task("traffic_hijacker.py")

            now = time.time()

            # 1. Forwarder Engine (Safe for Laptop IP)
            if now - last_forward > INTERVAL_FORWARD:
                run_script("auto_forwarder.py", timeout=900)
                last_forward = now

            # 2. Promo Engine (DM Growth) - Best run from Laptop (Local IP)
            if now - last_promo > INTERVAL_PROMO:
                if os.path.exists("scraped_leads.txt"):
                    run_script("promo_contacts_optimized.py", timeout=3600)
                    run_script("promo_report.py", timeout=300)
                else:
                    print("[!] No leads found. Cloud scraper will run later.")
                last_promo = now

            # 3. Daily Progress Report
            if now - last_report > INTERVAL_REPORT:
                run_script("daily_report.py", timeout=300)
                last_report = now
            
            time.sleep(300)
             
    except KeyboardInterrupt:
        print("\n[!] Orchestrator stopped by user.")
    except Exception as e:
        print(f"\n[FATAL] Orchestrator crashed: {e}")
    finally:
        if 'hijacker_process' in locals() and hijacker_process:
            hijacker_process.terminate()
            print("[*] Terminated AI Traffic Hijacker.")

if __name__ == "__main__":
    main()