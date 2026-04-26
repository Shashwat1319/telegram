import subprocess
import time
import os
import sys
from datetime import datetime

# Configuration for PROMOTION ONLY (Laptop Mode)
# Main deals and reports are now handled by GitHub Actions (Cloud)
INTERVAL_PROMO = 3 * 60 * 60  # 3 hours (Growth DM)
INTERVAL_SCRAPER = 24 * 60 * 60 # 24 hours (New Leads Scrape)
INTERVAL_FORWARD = 60 * 60     # 1 hour (Auto Forwarding)

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

def main():
    print("="*50)
    print(" ARZI HYBRID ORCHESTRATOR v3.1 - LAPTOP MODE ")
    print("="*50)
    print("Note: Deals, Reports & Website are handled by Cloud.")
    print(f"Start Time: {datetime.now()}")
    
    last_promo = 0
    last_scraper = 0
    last_forward = 0

    print("[*] Entering Hybrid Loop...")
    try:
        while True:
            now = time.time()

            # 1. Forwarder Engine (Safe for Laptop IP)
            if now - last_forward > INTERVAL_FORWARD:
                run_script("auto_forwarder.py", timeout=900)
                last_forward = now

            # 2. Promo Engine (DM Growth) - Best run from Laptop (Local IP)
            if now - last_promo > INTERVAL_PROMO:
                if os.path.exists("scraped_leads.txt"):
                    run_script("promo_contacts.py", timeout=3600) # 1h timeout
                else:
                    print("[!] No leads found. Scraper will run later.")
                last_promo = now

            # 2. Scraper (New Leads for Promotion)
            if now - last_scraper > INTERVAL_SCRAPER:
                run_script("scrape_active_members.py", timeout=3600) # 1h timeout
                last_scraper = now
            
            # Sleep for 5 minutes between checks
            time.sleep(300)
            
    except KeyboardInterrupt:
        print("\n[!] Orchestrator stopped by user.")
    except Exception as e:
        print(f"\n[FATAL] Orchestrator crashed: {e}")

if __name__ == "__main__":
    main()
