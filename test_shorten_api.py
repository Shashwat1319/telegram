import requests
from urllib.parse import quote

CLICK_TRACKER_URL = "https://budgetdeals-tracker-737523f4.netlify.app"
TEST_URL = "https://www.amazon.in/dp/B0BTNT8X6K?tag=shashwat022-21"

def test_shorten():
    print(f"[*] Requesting short link for: {TEST_URL}")
    api_url = f"{CLICK_TRACKER_URL}/go?action=shorten&url={quote(TEST_URL)}"
    
    try:
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            short_url = data.get("shortUrl")
            print(f"\n[SUCCESS] Short Link Created: {short_url}")
            print(f"\n👉 Is link ko Telegram mein paste karke check kariye:")
            print(f"   {short_url}")
        else:
            print(f"[FAILED] Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_shorten()
