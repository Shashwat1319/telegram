import subprocess
import time
import os
import sys
from datetime import datetime

# Configuration for PROMOTION ONLY (Laptop Mode)
# Main deals and reports are now handled by GitHub Actions (Cloud)
INTERVAL_PROMO = 3 * 60 * 60  # 3 hours (Growth DM)
INTERVAL_SCRAPER = 12 * 60 * 60 # 12 hours (High-Intent Leads Scrape)
INTERVAL_FORWARD = 15 * 60     # 15 minutes (Growth Burst Mode)
INTERVAL_REPORT = 12 * 60 * 60 # 12 hours (Daily Progress Report)
INTERVAL_UNDER99 = 2 * 60 * 60 # 2 hours (High-Conversion Loot)
INTERVAL_MAIN_POST = 1 * 60 * 60 # 1 hour (Branded Deals)
INTERVAL_GROWTH = 2 * 60 * 60    # 2 hours (Automated Member Growth)

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
        # Use sys.executable to ensure we use the same environment
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
        # Commit local tracker changes if any to prevent merge conflicts
        subprocess.run(["git", "add", "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Local tracker auto-sync"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Pull changes cleanly
        result = subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, text=True)
        if "conflict" in result.stderr.lower() or result.returncode != 0:
            print("[!] Git conflict detected during sync. Aborting rebase and forcing cloud state...")
            subprocess.run(["git", "rebase", "--abort"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "reset", "--hard", "origin/main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("[SUCCESS] Local repository is in sync with GitHub!")
    except Exception as e:
        print(f"[!] Error during git sync: {e}")

def main():
    print("="*50)
    print(" ARZI HYBRID ORCHESTRATOR v3.1 - LAPTOP MODE ")
    print("="*50)
    print("Note: Deals, Reports & Website are handled by Cloud, but local reports are enabled.")
    print(f"Start Time: {datetime.now()}")
    
    last_promo = 0
    last_scraper = 0
    last_forward = 0
    last_report = 0
    last_under99 = 0
    last_main_post = 0
    last_growth = 0

    print("[*] Starting AI Traffic Hijacker (Background)...")
    hijacker_process = start_background_task("traffic_hijacker.py")

    print("[*] Entering Hybrid Loop...")
    try:
        while True:
            # Sync with Cloud disabled to keep product.json static
            # git_sync()

            # Check if hijacker died, restart it
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
                    run_script("promo_contacts.py", timeout=3600) # 1h timeout
                    # Send Promo Report after finishing the promo cycle
                    run_script("promo_report.py", timeout=300)
                else:
                    print("[!] No leads found. Scraper will run later.")
                last_promo = now

            # 3. Scraper (New Leads for Promotion)
            if now - last_scraper > INTERVAL_SCRAPER:
                run_script("scrape_active_members.py", timeout=3600) # 1h timeout
                last_scraper = now
                
            # 4. Under-₹99 High Conversion Loot (PAUSED for High-Intent Pivot)
            # if now - last_under99 > INTERVAL_UNDER99:
            #     run_script("under_99_loot.py", timeout=900)
            #     last_under99 = now

            # 5. Branded Main Post (from product.json)
            if now - last_main_post > INTERVAL_MAIN_POST:
                run_script("bot_post.py", timeout=300)
                last_main_post = now

            # 6. Daily Progress Report
            if now - last_report > INTERVAL_REPORT:
                run_script("daily_report.py", timeout=300)
                last_report = now

            # 7. Automated Member Growth Engine
            if now - last_growth > INTERVAL_GROWTH:
                run_script("member_growth.py", timeout=900)
                last_growth = now
            
            # Sleep for 5 minutes between checks
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
