"""Amazon Creators API (PA-API successor) eligibility probe.

Reads credentials from the Amazon CSV export, fetches a token, then calls
getItems. Amazon gates data access behind qualifying sales, so a 403 with
reason=AssociateNotEligible means credentials are VALID but the account
hasn't met the sales threshold (10 qualified sales in trailing 30 days).

Usage:
    py creators_api_check.py            # human-readable output
    exit codes: 0 = eligible (API live)
                1 = valid creds, not eligible yet (403 AssociateNotEligible)
                2 = error (bad creds / network / config)
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

CREDS_CSV = os.getenv("CREATORS_CREDENTIALS_CSV", r"D:\Smartgahr-credentials.csv")
TOKEN_URL = "https://api.amazon.co.uk/auth/o2/token"
API_URL = "https://creatorsapi.amazon/catalog/v1/getItems"
MARKETPLACE = os.getenv("CREATORS_MARKETPLACE", "www.amazon.in")
PARTNER_TAG = os.getenv("AFFILIATE_ID_IN", "shashwat022-21")
STATUS_FILE = "creators_api_status.json"
TEST_ASIN = os.getenv("CREATORS_TEST_ASIN", "B0D1XD1ZV3")


def _post_json(url, data, headers=None, timeout=30):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _save(result):
    try:
        tmp = STATUS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        os.replace(tmp, STATUS_FILE)
    except Exception:
        pass


def check():
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "reason": "",
        "detail": "",
    }

    if not os.path.exists(CREDS_CSV):
        result["detail"] = f"credentials file not found: {CREDS_CSV}"
        _save(result)
        return result
    try:
        with open(CREDS_CSV, newline="", encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
    except Exception as e:
        result["detail"] = f"could not read credentials CSV: {e}"
        _save(result)
        return result

    client_id = (row.get("Credential Id") or row.get("Credential ID") or "").strip()
    client_secret = (row.get("Secret") or "").strip()
    if not client_id or not client_secret:
        result["detail"] = "Credential Id / Secret missing in CSV"
        _save(result)
        return result

    # 1. Token
    code, body = _post_json(TOKEN_URL, {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "creatorsapi::default",
    })
    if code != 200:
        result["detail"] = f"token request failed: HTTP {code} {body[:200]}"
        _save(result)
        return result
    try:
        token = json.loads(body)["access_token"]
    except Exception:
        result["detail"] = "token response missing access_token"
        _save(result)
        return result

    # 2. getItems (data call — gated by sales eligibility)
    payload = {
        "itemIds": [TEST_ASIN],
        "itemIdType": "ASIN",
        "marketplace": MARKETPLACE,
        "partnerTag": PARTNER_TAG,
        "resources": ["images.primary.small", "itemInfo.title"],
    }
    code, body = _post_json(API_URL, payload, headers={
        "Authorization": f"Bearer {token}",
        "x-marketplace": MARKETPLACE,
    })
    if code == 200:
        result["status"] = "eligible"
        result["detail"] = "API access LIVE — qualifying sales met"
    elif code == 403:
        try:
            err = json.loads(body)
            reason = err.get("reason", "")
            msg = err.get("message", "")
        except Exception:
            reason, msg = "", body[:200]
        if reason == "AssociateNotEligible":
            result["status"] = "not_eligible"
            result["reason"] = reason
            result["detail"] = (
                f"credentials VALID, but sales threshold not met: {msg} "
                "(10 qualified sales in trailing 30 days)"
            )
        else:
            result["status"] = "error"
            result["reason"] = reason
            result["detail"] = f"HTTP 403: {msg or body[:200]}"
    else:
        result["status"] = "error"
        result["detail"] = f"HTTP {code}: {body[:300]}"
    _save(result)
    return result


def main():
    reconf = getattr(sys.stdout, "reconfigure", None)
    if reconf:
        try:
            reconf(encoding="utf-8", errors="replace")
        except Exception:
            pass
    r = check()
    icon = {"eligible": "✅", "not_eligible": "⏳", "error": "❌"}.get(r["status"], "❓")
    print(f"{icon} Creators API [{r['status']}] @ {r['checked_at']}")
    if r.get("reason"):
        print(f"   reason: {r['reason']}")
    if r.get("detail"):
        print(f"   {r['detail']}")
    return {"eligible": 0, "not_eligible": 1}.get(r["status"], 2)


if __name__ == "__main__":
    sys.exit(main())
