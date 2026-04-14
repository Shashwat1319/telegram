"""
Facebook Page Token Generator (PERMANENT)
---------------------------------------
Run this script, it will open your browser automatically.
It will exchange the short-lived token for a PERMANENT Page token
and automatically update your .env file.
"""
import http.server
import webbrowser
import urllib.parse
import threading
import os
import requests
import sys
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
APP_ID = os.getenv("FB_APP_ID", "891489110558398")
APP_SECRET = os.getenv("FB_APP_SECRET")
PAGE_ID = os.getenv("FB_PAGE_ID", "636352506226349")
REDIRECT_URI = "http://localhost:3000"

if not APP_SECRET:
    print("[ERROR] FB_APP_SECRET missing in .env. Cannot generate permanent token.")
    sys.exit(1)

# Scopes needed for automated Page posting
SCOPES = "public_profile,pages_show_list,pages_manage_posts,pages_read_engagement,business_management"

oauth_url = (
    f"https://www.facebook.com/dialog/oauth?"
    f"client_id={APP_ID}"
    f"&scope={SCOPES}"
    f"&response_type=token"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
)

token_received = threading.Event()

class TokenHandler(http.server.BaseHTTPRequestHandler):
    def update_env_file(self, new_token):
        env_path = ".env"
        if not os.path.exists(env_path):
            print("[!] .env file not found. Skipping auto-update.")
            return

        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        found = False
        for line in lines:
            if line.startswith("FB_ACCESS_TOKEN="):
                new_lines.append(f"FB_ACCESS_TOKEN={new_token}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"FB_ACCESS_TOKEN={new_token}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print("[*] .env file successfully updated with the PERMANENT token!")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        if "/token" in self.path:
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            short_token = params.get("access_token", [""])[0]
            if short_token:
                print("\n[*] Initial token received. Exchanging for Permanent Page Token...")
                try:
                    # Step 1: Exchange for Long-lived User Token (60 days)
                    exchange_url = "https://graph.facebook.com/v19.0/oauth/access_token"
                    p1 = {
                        "grant_type": "fb_exchange_token",
                        "client_id": APP_ID,
                        "client_secret": APP_SECRET,
                        "fb_exchange_token": short_token
                    }
                    r1 = requests.get(exchange_url, params=p1).json()
                    long_lived_token = r1.get("access_token")

                    if not long_lived_token:
                        print(f"[ERROR] Could not get long-lived token: {r1}")
                        return

                    # Step 2: Get Permanent Page Access Token for our specific Page
                    page_url = f"https://graph.facebook.com/v19.0/{PAGE_ID}"
                    p2 = {
                        "fields": "access_token",
                        "access_token": long_lived_token
                    }
                    r2 = requests.get(page_url, params=p2).json()
                    permanent_token = r2.get("access_token")

                    if permanent_token:
                        print(f"\n[SUCCESS] Permanent Page Access Token: {permanent_token[:15]}...")
                        self.update_env_file(permanent_token)
                        self.wfile.write(b"<h1>SUCCESS! .env updated with Permanent Token!</h1><p>You can close this tab now.</p>")
                        token_received.set()
                    else:
                        print(f"[ERROR] Could not get page token. Ensure you selected the correct page. Response: {r2}")
                except Exception as e:
                    print(f"[ERROR] Exchange logic failed: {e}")
            return
        
        # Initial HTML to catch the hash fragment
        html = """
        <html><body>
        <h2>Finalizing your Permanent Token...</h2>
        <script>
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const token = params.get('access_token');
            if (token) {
                fetch('/token?access_token=' + token).then(() => {
                    document.body.innerHTML = '<h1>SUCCESS! Check your terminal.</h1>';
                });
            } else {
                document.body.innerHTML = '<h1>Error: No token found.</h1>';
            }
        </script></body></html>
        """.encode()
        self.wfile.write(html)
    
    def log_message(self, format, *args): pass

def start_server():
    server = http.server.HTTPServer(("localhost", 3000), TokenHandler)
    server.handle_request() # Wait for browser redirect
    server.handle_request() # Wait for JS to send token back
    server.server_close()

print("[*] Starting local server...")
print("[*] Opening Facebook Login. This will only take 10 seconds.")
threading.Thread(target=start_server, daemon=True).start()
webbrowser.open(oauth_url)

token_received.wait(timeout=120)
print("\n[Done] Script finished. Your bot is now ready for Permanent FB Posting!")
