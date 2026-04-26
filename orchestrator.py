import subprocess
import time
import os
import sys
from datetime import datetime

# Configuration
INTERVAL_MAIN = 45 * 60       # 45 minutes (Scraping + Posting + Forwarding)
INTERVAL_PROMO = 3 * 60 * 60  # 3 hours (Growth DM)
INTERVAL_POLL = 6 * 60 * 60   # 6 hours (Engagement)
INTERVAL_REPORT = 30 * 60     # 30 minutes (Promo Report)
INTERVAL_SCRAPER = 24 * 60 * 60 # 24 hours (New Leads Scrape)

def run_script(script_name, timeout=300):
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

def main():
    print("="*50)
    print(" ARZI GROWTH ORCHESTRATOR v2.1 - 24/7 MODE ")
    print("="*50)
    print(f"Start Time: {datetime.now()}")
    
    # Initialize timers to 0 so they run immediately on first loop
    last_main = 0
    last_promo = 0
    last_poll = 0
    last_report = 0
    last_scraper = 0

    print("[*] Entering Main Loop...")
    try:
        while True:
            now = time.time()

            # 1. Main Engine: trending_updater.py (Every 45m)
            if now - last_main > INTERVAL_MAIN:
                run_script("trending_updater.py", timeout=600) # 10m timeout for scraping
                last_main = now

            # 2. Promo Engine (Every 3h)
            if now - last_promo > INTERVAL_PROMO:
                if os.path.exists("scraped_leads.txt"):
                    run_script("promo_contacts.py", timeout=1800) # 30m timeout for long sending
                last_promo = now

            # 3. Engagement (Every 6h)
            if now - last_poll > INTERVAL_POLL:
                run_script("auto_engagement.py")
                last_poll = now

            # 4. Promo Report (Every 30m)
            if now - last_report > INTERVAL_REPORT:
                run_script("promo_report.py")
                last_report = now

            # 5. Scraper (Every 24h)
            if now - last_scraper > INTERVAL_SCRAPER:
                run_script("scrape_active_members.py", timeout=3600) # 1h timeout
                last_scraper = now

            # Daily Report at 8 AM and 8 PM (approx)
            current_hour = datetime.now().hour
            if current_hour in [8, 20] and (now - last_report > 3600): # Once during the hour
                 run_script("daily_report.py")
            
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n[!] Orchestrator stopped by user.")
    except Exception as e:
        print(f"\n[FATAL] Orchestrator crashed: {e}")

if __name__ == "__main__":
    main()
