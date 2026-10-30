"""Set up professional, keyword-rich Pinterest boards for SmartGahr.

Flow: OAuth (one browser click) -> save token -> list existing boards ->
create missing boards with SEO-friendly names + descriptions ->
optionally rename the old demo board.

Run:  py pinterest_boards.py
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
SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"
STATE = "smartgahr-boards-2026"

# Professional boards: keyword-rich names (Pinterest = search engine)
BOARDS = [
    {
        "name": "Amazon Deals Under Rs.999 India — Daily Loot Finds",
        "description": "Verified Amazon India deals under Rs.999 with 40%+ off. "
                       "Daily loot deals on electronics, home, kitchen and more. "
                       "New deals every day — smart shopping, real discounts. "
                       "smartgahr.netlify.app",
    },
    {
        "name": "Kitchen Finds India — Home & Kitchen Essentials",
        "description": "Best home and kitchen essentials from Amazon India — "
                       "pressure cookers, induction cooktops, bottles, jugs and "
                       "daily-use kitchen tools under Rs.999 with big discounts.",
    },
    {
        "name": "Electronics Deals India — Earbuds & Gadgets",
        "description": "Best electronics deals in India — TWS earbuds, smartwatches, "
                       "power banks, cables and gadgets at up to 78% off on Amazon. "
                       "Verified deals under Rs.999.",
    },
    {
        "name": "Home Improvement & Electric Appliances India",
        "description": "Ceiling fans, LED bulbs, switches, mosquito repellents and "
                       "home improvement essentials — verified Amazon India deals "
                       "with 40%+ discounts.",
    },
]

# Old demo board to rename (from pinterest_demo.py) instead of leaving clutter
RENAME_MAP = {
    "Kitchen Finds Demo": "Amazon Deals Under Rs.999 India — Daily Loot Finds",
}


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


def save_token(token):
    """Persist token so future scripts skip OAuth."""
    path = os.path.join(ROOT, ".env")
    lines = []
    if os.path.exists(path):
        lines = open(path, encoding="utf-8").read().splitlines()
    lines = [l for l in lines if not l.startswith("PINTEREST_ACCESS_TOKEN=")]
    lines.append(f"PINTEREST_ACCESS_TOKEN={token}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


captured: dict = {"code": None, "state": None, "error": None}


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
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def log_message(self, format, *args):  # noqa: A002
        pass


def get_token() -> str:
    """Reuse saved token, else run OAuth consent flow."""
    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if token:
        r = requests.get(f"{API}/user_account",
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if r.status_code == 200:
            print(f"Using saved token (@{r.json().get('username')})")
            return token
        print("Saved token invalid/expired — running OAuth flow again...")
    return run_oauth()


def run_oauth() -> str:
    app_id = os.environ.get("PINTEREST_APP_ID", "")
    app_secret = os.environ.get("PINTEREST_APP_SECRET", "")
    redirect = os.environ.get("PINTEREST_REDIRECT_URI", "http://localhost:8080/callback")
    if not app_id or not app_secret:
        sys.exit("PINTEREST_APP_ID / PINTEREST_APP_SECRET missing in .env")

    u = urllib.parse.urlparse(redirect)
    try:
        srv = HTTPServer((u.hostname or "localhost", u.port or 80), Callback)
    except OSError as e:
        sys.exit(f"Could not bind {redirect}: {e}")
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    auth = "https://www.pinterest.com/oauth/?" + urllib.parse.urlencode(
        {"client_id": app_id, "redirect_uri": redirect, "response_type": "code",
         "scope": SCOPES, "state": STATE}
    )
    print(f"\nOpening Pinterest consent screen...\n{auth}")
    webbrowser.open(auth)
    print("Browser mein 'Give access' click karo (2 min timeout)...")

    deadline = time.time() + 120
    while time.time() < deadline and not captured["code"] and not captured["error"]:
        time.sleep(0.5)
    if captured["error"] or not captured["code"]:
        sys.exit(f"OAuth failed: {captured['error'] or 'timeout'}")

    r = requests.post(
        f"{API}/oauth/token", auth=(app_id, app_secret),
        data={"grant_type": "authorization_code", "code": captured["code"],
              "redirect_uri": redirect},
        timeout=30,
    )
    if r.status_code != 200:
        sys.exit(f"Token exchange failed: HTTP {r.status_code} {r.text[:300]}")
    token = r.json()["access_token"]
    save_token(token)
    print("Token saved to .env (PINTEREST_ACCESS_TOKEN)")
    return token


def main():
    print("=" * 60)
    print(" SMARTGAHR — professional Pinterest boards setup")
    print("=" * 60)

    load_env()
    token = get_token()
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. List existing boards
    print("\n[1] Existing boards:")
    r = requests.get(f"{API}/boards", params={"page_size": 100}, headers=h, timeout=30)
    if r.status_code != 200:
        sys.exit(f"GET /boards failed: HTTP {r.status_code} {r.text[:300]}")
    existing = {b["name"]: b for b in r.json().get("items", [])}
    for b in existing.values():
        print(f"    - {b['name']}  (id={b['id']})")

    # 2. Rename old demo board if present (avoids duplicate clutter)
    print("\n[2] Renaming old demo board (if any):")
    renamed = 0
    for old, new in RENAME_MAP.items():
        if old in existing and new not in existing:
            b = existing.pop(old)
            rr = requests.patch(f"{API}/boards/{b['id']}", headers=h,
                              json={"name": new, "description":
                                    BOARDS[0]["description"]}, timeout=30)
            if rr.status_code == 200:
                print(f"    OK  '{old}' -> '{new}'")
                renamed += 1
            else:
                print(f"    FAIL '{old}': HTTP {rr.status_code} {rr.text[:200]}")

    # 3. Create missing professional boards
    print("\n[3] Creating professional boards:")
    created = 0
    for b in BOARDS:
        if b["name"] in existing:
            print(f"    SKIP (exists): {b['name']}")
            continue
        rr = requests.post(f"{API}/boards", headers=h,
                           json={"name": b["name"], "description": b["description"]},
                           timeout=30)
        if rr.status_code in (200, 201):
            print(f"    OK  created: {b['name']}")
            created += 1
        else:
            print(f"    FAIL: {b['name']} — HTTP {rr.status_code} {rr.text[:200]}")

    print("\n" + "=" * 60)
    print(f" DONE — created {created}, renamed {renamed}")
    print(" Pinterest profile kholke boards check kar le.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
