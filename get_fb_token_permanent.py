import http.server
import webbrowser
import urllib.parse
import threading
import requests
import os
import sys
import time
from dotenv import load_dotenv

# Load configuration
load_dotenv()

APP_ID = os.getenv("FB_APP_ID")
APP_SECRET = os.getenv("FB_APP_SECRET")
PAGE_ID = os.getenv("FB_PAGE_ID")
REDIRECT_URI = "http://localhost:3000"
SCOPES = "public_profile,pages_show_list,pages_manage_posts,pages_read_engagement,business_management"

if not APP_ID or not APP_SECRET or not PAGE_ID:
    print("[ERROR] FB_APP_ID, FB_APP_SECRET, or FB_PAGE_ID missing in .env")
    sys.exit(1)

token_received = threading.Event()
received_token = None

class TokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global received_token
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        if "access_token" in self.path:
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            received_token = params.get("access_token", [""])[0]
            if received_token:
                self.wfile.write(b"<h1>SUCCESS! Check your terminal to complete the permanent exchange.</h1>")
                token_received.set()
                return
        
        html = """
        <html><body>
        <h2>Fetching your initial token...</h2>
        <script>
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const token = params.get('access_token');
            if (token) {
                document.body.innerHTML = '<h1>Received! Closing...</h1>';
                fetch('/token?access_token=' + token);
            } else {
                document.body.innerHTML = '<h1>Error: No token found. Try again.</h1>';
            }
        </script>
        </body></html>
        """.encode()
        self.wfile.write(html)
    
    def log_message(self, format, *args):
        pass

def start_server():
    server = http.server.HTTPServer(("localhost", 3000), TokenHandler)
    server.handle_request()
    server.handle_request()
    server.server_close()

def exchange_for_permanent(short_token):
    print("\n--- Phase 2: Exchanging for Permanent Token ---")
    
    # 1. Exchange Short-lived User Token -> Long-lived User Token (60 days)
    print("[*] Exchanging for Long-lived User Token...")
    url_exchange = (
        f"https://graph.facebook.com/v19.0/oauth/access_token?"
        f"grant_type=fb_exchange_token&"
        f"client_id={APP_ID}&"
        f"client_secret={APP_SECRET}&"
        f"fb_exchange_token={short_token}"
    )
    r_long_user = requests.get(url_exchange)
    data_long_user = r_long_user.json()
    
    if "error" in data_long_user:
        print(f"[FAILED] User Token Exchange: {data_long_user['error'].get('message')}")
        return None
    
    long_user_token = data_long_user.get("access_token")
    print("[OK] Long-lived User Token received.")
    
    # 2. Get Never-Expiring Page Token
    print(f"[*] Fetching Never-Expiring Page Token for Page ID {PAGE_ID}...")
    url_accounts = f"https://graph.facebook.com/v19.0/me/accounts?access_token={long_user_token}"
    r_accounts = requests.get(url_accounts)
    data_accounts = r_accounts.json()
    
    if "error" in data_accounts:
        print(f"[FAILED] Page Token Fetch: {data_accounts['error'].get('message')}")
        return None
    
    page_token = None
    page_name = ""
    for page in data_accounts.get("data", []):
        if page.get("id") == PAGE_ID:
            page_token = page.get("access_token")
            page_name = page.get("name")
            break
            
    if not page_token:
        print(f"[FAILED] Could not find Page ID {PAGE_ID} in the list of pages you manage.")
        return None
    
    print(f"[OK] Permanent Page Token for '{page_name}' received.")
    
    # 3. Verify Permanence
    print("[*] Verifying permanence via Debug API...")
    url_debug = f"https://graph.facebook.com/debug_token?input_token={page_token}&access_token={page_token}"
    r_debug = requests.get(url_debug)
    debug_data = r_debug.json().get("data", {})
    
    expires_at = debug_data.get("expires_at", 0)
    if expires_at == 0:
        print("[SUCCESS] TOKEN IS PERMANENT (Never Expire)!")
    else:
        expiry_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))
        print(f"[WARNING] Token is NOT permanent. It expires at: {expiry_date}")
        
    return page_token

def update_env(new_token):
    print(f"[*] Updating .env with the new token...")
    with open(".env", "r") as f:
        lines = f.readlines()
    
    updated = False
    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("FB_ACCESS_TOKEN="):
                f.write(f"FB_ACCESS_TOKEN={new_token}\n")
                updated = True
            else:
                f.write(line)
        if not updated:
            f.write(f"FB_ACCESS_TOKEN={new_token}\n")
            
    print("[OK] .env updated.")

def main():
    print("--- Facebook Permanent Token Generator ---")
    print(f"[*] APP ID: {APP_ID}")
    
    oauth_url = (
        f"https://www.facebook.com/dialog/oauth?"
        f"client_id={APP_ID}"
        f"&scope={SCOPES}"
        f"&response_type=token"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    )
    
    # Start server
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("[*] Opening Browser for Login...")
    webbrowser.open(oauth_url)
    
    print("[*] Waiting for initial token (timeout 2 min)...")
    if token_received.wait(timeout=120):
        permanent_token = exchange_for_permanent(received_token)
        if permanent_token:
            update_env(permanent_token)
            print("\nCongratulations! Your script is now running with a PERMANENT Facebook token.")
            print("You don't need to run this script again.")
        else:
            print("\n[FAILED] Permanent exchange failed. Please check the errors above.")
    else:
        print("\n[TIMEOUT] User did not login in time.")

if __name__ == "__main__":
    main()
