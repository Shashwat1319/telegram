import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")

def exercise_fb_permissions():
    """
    Makes API calls to exercise permissions for Facebook App Review.
    This helps move items like 'public_profile', 'pages_show_list', etc. to 'Completed'.
    """
    if not FB_ACCESS_TOKEN:
        print("Error: FB_ACCESS_TOKEN missing. Please run get_fb_token.py first.")
        return

    print("--- Exercising Facebook Permissions for App Review ---")
    
    # 1. Exercise 'public_profile'
    print("[*] Exercising 'public_profile'...")
    url_me = f"https://graph.facebook.com/v19.0/me?fields=id,name,picture&access_token={FB_ACCESS_TOKEN}"
    r_me = requests.get(url_me)
    if r_me.status_code == 200:
        print(f"    [SUCCESS] User Info: {r_me.json().get('name')}")
    else:
        print(f"    [FAILED] {r_me.text}")

    # 2. Exercise 'pages_show_list'
    print("[*] Exercising 'pages_show_list'...")
    url_accounts = f"https://graph.facebook.com/v19.0/me/accounts?fields=name,access_token,tasks&access_token={FB_ACCESS_TOKEN}"
    r_accounts = requests.get(url_accounts)
    if r_accounts.status_code == 200:
        pages = r_accounts.json().get('data', [])
        print(f"    [SUCCESS] Found {len(pages)} pages.")
    else:
        print(f"    [FAILED] {r_accounts.text}")

    # 3. Exercise 'pages_manage_metadata'
    if FB_PAGE_ID:
        print("[*] Exercising 'pages_manage_metadata'...")
        url_page = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}?fields=about,emails,name,category&access_token={FB_ACCESS_TOKEN}"
        r_page = requests.get(url_page)
        if r_page.status_code == 200:
            print(f"    [SUCCESS] Page Info: {r_page.json().get('name')}")
        else:
            print(f"    [FAILED] {r_page.text}")

    # 4. Exercise 'pages_read_engagement' & 'business_management'
    if FB_PAGE_ID:
        print("[*] Exercising 'pages_read_engagement'...")
        url_insights = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/insights?metric=page_impressions_unique&access_token={FB_ACCESS_TOKEN}"
        r_insights = requests.get(url_insights)
        if r_insights.status_code == 200:
            print(f"    [SUCCESS] Insights fetched.")
        else:
            print(f"    [FAILED] {r_insights.text}")

    # 5. Exercise 'Live Video API' (publish_video)
    if FB_PAGE_ID:
        print("[*] Exercising 'Live Video API'...")
        url_live = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/live_videos?access_token={FB_ACCESS_TOKEN}"
        r_live = requests.get(url_live)
        if r_live.status_code == 200:
            print(f"    [SUCCESS] Live Video list fetched.")
        else:
            print(f"    [FAILED] {r_live.text}")

    print("\n--- Done! Refresh your Facebook App Review Dashboard in a few minutes. ---")

if __name__ == "__main__":
    exercise_fb_permissions()
