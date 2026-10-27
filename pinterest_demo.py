"""Pinterest OAuth live demo - Kitchen Finds India (Standard-access video).

Flow: local callback server -> browser consent screen -> token exchange ->
user_accounts -> create board -> create pin (all live API calls).

Run:  py pinterest_demo.py
"""
import os
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
API = "https://api.pinterest.com/v5"
SCOPES = "boards:write,pins:write,user_accounts:read"
STATE = "kfinds2026"
IMAGE_URL = "https://budgetdeals-tracker-737523f4.netlify.app/og-image.jpg"
LINK_URL = "https://budgetdeals-tracker-737523f4.netlify.app/kitchenfinds/"

captured: dict = {"code": None, "state": None, "error": None}


def load_env():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k.startswith("PINTEREST_"):
            os.environ.setdefault(k, v)


load_env()
APP_ID = os.environ.get("PINTEREST_APP_ID", "")
APP_SECRET = os.environ.get("PINTEREST_APP_SECRET", "")
REDIRECT_URI = os.environ.get("PINTEREST_REDIRECT_URI", "http://localhost:8080/callback")


def step(n, msg):
    print(f"\n[STEP {n}] {msg}", flush=True)


def ok(msg):
    print(f"        OK   -> {msg}", flush=True)


def fail(msg, hint=None):
    print(f"        FAIL -> {msg}", flush=True)
    if hint:
        print(f"        HINT -> {hint}", flush=True)


class Callback(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        captured["code"] = qs.get("code", [None])[0]
        captured["state"] = qs.get("state", [None])[0]
        captured["error"] = qs.get("error", [None])[0]
        body = (
            "<html><body style='font-family:sans-serif;padding:60px;text-align:center'>"
            "<h2>Authorized &#9989;</h2>"
            "<p>You can close this tab and return to the terminal.</p>"
            "</body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        pass


def main():
    print("=" * 62)
    print(" KITCHEN FINDS INDIA - Pinterest OAuth live demo")
    print("=" * 62)

    if not APP_ID or not APP_SECRET:
        fail("PINTEREST_APP_ID / PINTEREST_APP_SECRET missing in .env")
        return 1

    u = urllib.parse.urlparse(REDIRECT_URI)
    port = u.port or (443 if u.scheme == "https" else 80)
    path = u.path or "/"
    if u.scheme != "http" or not u.hostname:
        fail(f"Unsupported redirect URI: {REDIRECT_URI}")
        return 1

    step(1, f"Starting callback server on {u.hostname}:{port}{path}")
    print(f"        NOTE: App Settings > Redirect URIs must contain exactly: {REDIRECT_URI}")
    try:
        srv = HTTPServer((u.hostname, port), Callback)
    except OSError as e:
        fail(f"Could not bind {u.hostname}:{port} - {e}")
        return 1
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ok("callback server up")

    step(2, "Opening Pinterest consent screen in browser")
    auth = "https://www.pinterest.com/oauth/?" + urllib.parse.urlencode(
        {
            "client_id": APP_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
            "state": STATE,
        }
    )
    print(f"        URL: {auth}")
    webbrowser.open(auth)

    step(3, "Waiting for YOUR click on 'Give access' (up to 5 minutes)")
    deadline = time.time() + 300
    while time.time() < deadline and not captured["code"] and not captured["error"]:
        time.sleep(0.5)
    if captured["error"]:
        fail(f"Pinterest returned: {captured['error']}")
        return 1
    if not captured["code"]:
        fail("Timed out - no authorization received", "Browser me consent screen check karo")
        return 1
    ok(f"authorization code received (state={captured['state']})")

    step(4, "Exchanging code for access token (POST /v5/oauth/token)")
    r = requests.post(
        f"{API}/oauth/token",
        auth=(APP_ID, APP_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": captured["code"],
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    if r.status_code != 200:
        fail(f"HTTP {r.status_code}: {r.text[:300]}",
             f"Redirect URI must match exactly: {REDIRECT_URI}")
        return 1
    token = r.json().get("access_token")
    ok(f"access token acquired (scope: {r.json().get('scope', '?')})")

    h = {"Authorization": f"Bearer {token}"}

    step(5, "GET /v5/user_accounts - reading your Pinterest profile")
    r = requests.get(f"{API}/user_accounts", headers=h, timeout=30)
    if r.status_code != 200:
        fail(f"HTTP {r.status_code}: {r.text[:300]}")
        return 1
    user = r.json()
    ok(f"logged in as @{user.get('username')} ({user.get('name', '')})")

    step(6, "POST /v5/boards - creating board 'Kitchen Finds Demo'")
    r = requests.post(
        f"{API}/boards",
        headers={**h, "Content-Type": "application/json"},
        json={"name": "Kitchen Finds Demo",
              "description": "Kitchen Finds India - live API demo board"},
        timeout=30,
    )
    if r.status_code != 200:
        fail(f"HTTP {r.status_code}: {r.text[:300]}",
             "403 = Pinterest Settings > Convert to business account (free), then retry")
        return 1
    board_id = r.json().get("id")
    ok(f"board created: {board_id}")

    step(7, "POST /v5/pins - creating a live pin on that board")
    r = requests.post(
        f"{API}/pins",
        headers={**h, "Content-Type": "application/json"},
        json={
            "board_id": board_id,
            "title": "Kitchen Finds India - Product Picks",
            "description": "Optimized kitchen product picks published live via the Pinterest API.",
            "link": LINK_URL,
            "media_source": {"source_type": "image_url", "url": IMAGE_URL},
        },
        timeout=30,
    )
    if r.status_code != 200:
        print(f"\n        FAIL -> HTTP {r.status_code}: {r.text[:300]}")
        print("        PARTIAL: STEP 5+6 (OAuth + live board creation) kaam kar rahe hain.")
        print("        Video me STEP 1-6 record karo - board creation bhi live integration hai.")
        print("        Pin 403 = Trial restriction; mujhe error paste kar do.")
        return 0
    pin_id = r.json().get("id")
    ok(f"pin created: {pin_id}")

    print("\n" + "=" * 62)
    print(" SUCCESS - board + pin created live via Pinterest API v5")
    print(" Ab browser me Pinterest profile kholo: board + pin dikhega")
    print(" Video yahin tak record rakho (Win+G stop) -> form me upload")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
