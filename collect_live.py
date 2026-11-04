#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pass 2 — collect reliable live data for every filled link in the new batch.

Slower pace (12s), alternating desktop/mobile UA, richer price/MRP extraction.
Writes link_live.json: [{idx, asin, url, title, price, mrp, rating, reviews,
in_stock, unavailable}] for index >= 50 rows with links.

Usage: py collect_live.py [--limit N]
"""
import json
import os
import re
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import requests

DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
ASIN_RE = re.compile(r"/(?:dp|gp/product|d)/([A-Z0-9]{10})(?:[/?]|$)", re.I)

OUT = "link_live.json"


def get(session, url, ua, tries=3):
    for i in range(tries):
        try:
            r = session.get(url, headers={"User-Agent": ua,
                                          "Accept-Language": "en-IN,en;q=0.9"},
                            timeout=30, allow_redirects=True)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(8 + i * 8)
    return None


def money(s):
    if not s:
        return None
    n = int(re.sub(r"\D", "", s))
    return n if 10 <= n <= 999999 else None


def extract(html, ua_label):
    out = {}
    t = re.search(r"<title[^>]*>([^<]{5,300})", html, re.I)
    out["title"] = t.group(1).split(" Amazon.in")[0].strip() if t else ""

    # selling price strategies (in priority order)
    price = None
    for pat in (
        r'id="corePrice_desktop_feature_div"[\s\S]{0,2500}?<span class="a-offscreen">₹([\d,]+)',
        r'id="corePrice_feature_div"[\s\S]{0,2500}?<span class="a-offscreen">₹([\d,]+)',
        r'id="price_inside_buybox"[^>]*>₹?([\d,]+)',
        r'data-a-color="price"[^>]*>.*?<span class="a-offscreen">₹([\d,]+)',
        r'<span class="a-price[^"]*" data-a-color="price"><span class="a-offscreen">₹([\d,]+)',
    ):
        m = re.search(pat, html)
        if m:
            price = money(m.group(1))
            if price:
                break
    out["price"] = price

    # MRP / strike-through
    mrp = None
    for pat in (
        r'<span class="a-price a-text-price[^"]*"[\s\S]{0,300}?<span class="a-offscreen">₹([\d,]+)',
        r'id="basisPrice"[\s\S]{0,400}?₹([\d,]+)',
        r'M\.?R\.?P\.?:?\s*</span>\s*<span[^>]*>\s*<span[^>]*>₹([\d,]+)',
        r'class="a-text-strike[^"]*"[^>]*>₹([\d,]+)',
    ):
        m = re.search(pat, html, re.I)
        if m:
            mrp = money(m.group(1))
            if mrp:
                break
    out["mrp"] = mrp

    m = re.search(r'acrPopover[^"]*"[^>]*title="([\d.]+) out of 5', html)
    out["rating"] = float(m.group(1)) if m else None
    m = re.search(r'id="acrCustomerReviewText"[^>]*>([\d,]+)\s*ratings?', html)
    out["reviews"] = int(re.sub(r"\D", "", m.group(1))) if m else None

    out["unavailable"] = "Currently unavailable" in html
    out["add_to_cart"] = 'id="add-to-cart-button"' in html
    out["in_stock"] = out["add_to_cart"] or (price is not None and not out["unavailable"])
    out["ua"] = ua_label
    return out


def main():
    args = sys.argv[1:]
    limit = 0
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    fix_only = "--fix" in args

    data = json.load(open("product.json", encoding="utf-8"))["products"]
    rows = [(i, p) for i, p in enumerate(data)
            if i >= 50 and (p.get("link") or "").strip()]

    prev = {}
    if os.path.exists(OUT):
        try:
            prev = {r["idx"]: r for r in json.load(open(OUT, encoding="utf-8"))}
        except Exception:
            prev = {}

    def needs_fix(rec):
        if rec is None:
            return True
        title = rec.get("title") or ""
        if not title or title == "Amazon.in":
            return True
        if rec.get("err"):
            return True
        price = rec.get("price")
        mrp = rec.get("mrp")
        if price is None:
            return True
        if mrp is None or mrp <= price:
            return True
        return False

    if fix_only:
        rows = [(i, p) for i, p in rows if needs_fix(prev.get(i))]
        print(f"--fix: refetching {len(rows)} bad row(s)")
    if limit:
        rows = rows[:limit]

    print(f"collecting live data for {len(rows)} links (15s pace, desktop UA) -> {OUT}")
    session = requests.Session()
    results = []
    for n, (idx, p) in enumerate(rows, 1):
        link = p["link"].strip()
        ua, ua_label = DESKTOP_UA, "desktop"

        # resolve link -> asin
        r = get(session, link, ua, tries=2)
        asin, final = None, None
        if r is not None:
            final = r.url
            m = ASIN_RE.search(final or "")
            asin = m.group(1).upper() if m else None

        rec = {"idx": idx, "card_name": p.get("name", ""), "link": link,
               "asin": asin, "final_url": final, "card_price": p.get("price"),
               "card_rating": p.get("rating")}
        if asin:
            time.sleep(12)
            r2 = get(session, f"https://www.amazon.in/dp/{asin}", ua, tries=2)
            if r2 is not None:
                rec.update(extract(r2.text, ua_label))
            else:
                rec["err"] = "page fetch failed after retries"
        else:
            rec["err"] = "could not resolve ASIN"

        results.append(rec)
        status = "ok" if rec.get("title") and rec.get("title") != "Amazon.in" else "DEGRADED"
        print(f"[{n:>2}/{len(rows)}] #{idx} {asin or '?'} {status} "
              f"price={rec.get('price')} mrp={rec.get('mrp')} "
              f"rating={rec.get('rating')} stock={rec.get('in_stock')} "
              f"| {(rec.get('title') or '')[:45]}")
        sys.stdout.flush()
        time.sleep(15)

    # MRP sanity: must be greater than selling price (bad regex grabs)
    for r in results:
        if r.get("mrp") is not None and r.get("price") is not None:
            if r["mrp"] <= r["price"]:
                r["mrp"] = None

    # merge with previous (keep any earlier good rows we skipped this round)
    merged = {r["idx"]: r for r in results}
    for k, v in prev.items():
        if k not in merged:
            merged[k] = v
    out = [merged[k] for k in sorted(merged)]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    good = sum(1 for r in results if r.get("title") and r.get("title") != "Amazon.in")
    print(f"\ndone: {good}/{len(results)} pages healthy; saved {OUT} ({len(out)} rows total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
