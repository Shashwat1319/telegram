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

def run_script(script_name):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] RUNNING: {script_name}")
    try:
        # Run directly to allow stdout to pass through
        result = subprocess.run([sys.executable, script_name])
        if result.returncode == 0:
            print(f"[SUCCESS] {script_name}")
        else:
            print(f"[ERROR] {script_name} failed with exit code {result.returncode}")
    except Exception as e:
        print(f"[CRITICAL] Could not run {script_name}: {e}")

def main():
    print("="*50)
    print(" ARZI GROWTH ORCHESTRATOR v2.0 - 24/7 MODE ")
    print("="*50)
    print(f"Start Time: {datetime.now()}")
    
    last_main = 0
    last_promo = 0
    last_poll = 0
    last_report = 0
    last_scraper = 0

    # Initial Report, Poll & First Promo Batch
    run_script("daily_report.py")
    run_script("auto_engagement.py")
    if os.path.exists("scraped_leads.txt"):
        run_script("promo_contacts.py")

    try:
        while True:
            now = time.time()

            # 1. Main Engine: trending_updater.py (Scrapes + Posts + Blogs + Forwards)
            if now - last_main > INTERVAL_MAIN:
                run_script("trending_updater.py")
                last_main = now

            # 2. Promo Engine (DM Growth)
            if now - last_promo > INTERVAL_PROMO:
                if os.path.exists("scraped_leads.txt"):
                    run_script("promo_contacts.py")
                last_promo = now

            # 3. Engagement (Polls)
            if now - last_poll > INTERVAL_POLL:
                run_script("auto_engagement.py")
                last_poll = now

            # 4. Promo Report (Every 30m)
            if now - last_report > INTERVAL_REPORT:
                run_script("promo_report.py")
                last_report = now

            # 5. Scraper (New Leads)
            if now - last_scraper > INTERVAL_SCRAPER:
                run_script("scrape_active_members.py")
                last_scraper = now

            # Daily Report (at Midnight local time - roughly)
            # Actually, I'll just run it every 12 hours for simplicity
            # (Handled by checking if hour is 0 or 12)
            
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n[!] Orchestrator stopped by user.")
    except Exception as e:
        print(f"\n[FATAL] Orchestrator crashed: {e}")

if __name__ == "__main__":
    main()
