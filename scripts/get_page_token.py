import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USER_TOKEN = os.getenv("FB_ACCESS_TOKEN")
PAGE_ID = os.getenv("FB_PAGE_ID")

def fetch_and_update_page_token():
    if not USER_TOKEN or not PAGE_ID:
        print("Error: FB_ACCESS_TOKEN or FB_PAGE_ID missing in .env")
        return

    print(f"[*] Fetching Page Token for Page ID: {PAGE_ID}...")
    
    url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={USER_TOKEN}"
    response = requests.get(url)
    data = response.json()

    if 'error' in data:
        print(f"[FAILED] API Error: {data['error'].get('message')}")
        return

    pages = data.get('data', [])
    page_token = None
    page_name = ""

    for page in pages:
        if page.get('id') == PAGE_ID:
            page_token = page.get('access_token')
            page_name = page.get('name')
            break

    if page_token:
        print(f"[SUCCESS] Found Page Token for '{page_name}'")
        
        # Update .env file
        with open(".env", "r") as f:
            lines = f.readlines()
        
        with open(".env", "w") as f:
            for line in lines:
                if line.startswith("FB_ACCESS_TOKEN="):
                    f.write(f"FB_ACCESS_TOKEN={page_token}\n")
                else:
                    f.write(line)
        
        print(f"[*] Updated .env with the Page Access Token.")
        print("[!] Now you can run: py fb_bot_post.py")
    else:
        print(f"[ERROR] Could not find Page ID {PAGE_ID} in your account. Please check if you selected the right page during login.")

if __name__ == "__main__":
    fetch_and_update_page_token()
