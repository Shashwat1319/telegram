import requests
import os
from dotenv import load_dotenv

load_dotenv()

CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL")

def fetch_stats():
    if not CLICK_TRACKER_URL:
        print("[ERROR] CLICK_TRACKER_URL not found in .env")
        return

    url = f"{CLICK_TRACKER_URL}/stats"
    try:
        print(f"[*] Fetching click stats from {url}...")
        response = requests.get(url)
        data = response.json()

        if data.get("status") == "success":
            print("\n" + "="*40)
            print(f"BUDGET DEALS - CLICK ANALYTICS")
            print("="*40)
            print(f"Total Clicks (All Time): {data.get('total_clicks', 0)}")
            print("-" * 40)
            print(f"{'DATE':<15} | {'CLICKS':<10}")
            print("-" * 40)
            
            # Show last 7 days from the history object
            history = data.get("history", {})
            # Sort keys (dates) in descending order
            sorted_dates = sorted(history.keys(), reverse=True)
            
            for date in sorted_dates:
                count = history[date]
                print(f"{date:<15} | {count:<10}")
            
            print("="*40)
            print("Note: Clicks are tracked from newly posted deals.")
        else:
            print(f"[!] API Error: {data.get('message')}")

    except Exception as e:
        print(f"[ERROR] Could not fetch stats: {e}")

if __name__ == "__main__":
    fetch_stats()
