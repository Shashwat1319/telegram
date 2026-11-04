#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA filled affiliate links against card copy.

For each product with a non-empty link (default: the new Diwali batch =
products whose link was empty at batch creation, i.e. index >= 50):
  1. resolve the link through redirects -> final amazon URL + ASIN
  2. fetch the product page -> title, deal price, MRP, rating, availability
  3. compare with card: name overlap, price sanity, rating, stock

Usage:
  py qa_links.py             # QA new batch (index >= 50) with links
  py qa_links.py --all       # QA every product with a link
  py qa_links.py --limit 10  # first N only (quick smoke test)

Exit code always 0 (report only). Reads product.json, writes nothing.
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

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept-Language": "en-IN,en;q=0.9",
}
ASIN_RE = re.compile(r"/(?:dp|gp/product|d)/([A-Z0-9]{10})(?:[/?]|$)", re.I)
PRICE_RE = re.compile(r"₹\s*([\d,]+)")
STOP = {"the", "for", "with", "and", "of", "in", "a", "pack", "set", "pc"}


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t) > 1}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def resolve(session, link):
    """Follow redirects -> (final_url, asin) or (None, err)."""
    try:
        r = session.get(link, headers=HEADERS, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return None, f"resolve failed: {type(e).__name__}"
    m = ASIN_RE.search(r.url or "")
    if m:
        return r.url, m.group(1).upper()
    return r.url, None  # landed on amazon but no ASIN (e.g. /deals)


def scrape(session, asin):
    """Fetch product page -> dict(title, price, mrp, rating, in_stock, raw_err)."""
    try:
        r = session.get(f"https://www.amazon.in/dp/{asin}", headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        return {"err": f"page failed: {type(e).__name__}"}
    html = r.text
    if r.status_code != 200:
        return {"err": f"page HTTP {r.status_code}"}

    title_m = re.search(r"<title[^>]*>([^<]{5,300})", html, re.I)
    title = title_m.group(1).split(" Amazon.in")[0].strip() if title_m else ""

    # selling price: prefer corePrice section, else first offscreen in buybox
    price = None
    for sec in (r'id="corePrice_desktop_feature_div"', r'id="corePrice_feature_div"',
                r'id="corePrice_feature_div"'):
        m = re.search(sec + r"[\s\S]{0,3000}?<span class=\"a-offscreen\">₹([\d,]+)", html)
        if m:
            price = m.group(1)
            break
    if not price:
        m = re.search(r'id="price_inside_buybox"[^>]*>₹([\d,]+)', html)
        if m:
            price = m.group(1)

    # MRP: strike-through price
    mrp = None
    m = re.search(r'<span class="a-price a-text-price[^"]*"[\s\S]{0,200}?a-offscreen">₹([\d,]+)', html)
    if m:
        mrp = m.group(1)

    rating_m = re.search(r'acrPopover[^"]*"[^>]*title="([\d.]+) out of 5', html)
    rating = float(rating_m.group(1)) if rating_m else None

    unavailable = "Currently unavailable" in html
    add_to_cart = 'id="add-to-cart-button"' in html
    in_stock = (not unavailable) and (add_to_cart or price is not None)

    return {"title": title, "price": price, "mrp": mrp, "rating": rating,
            "in_stock": in_stock}


def scrape_retry(session, asin, tries=3):
    """Retry when Amazon serves a degraded/bot page (no price+rating)."""
    sc = {}
    for i in range(tries):
        sc = scrape(session, asin)
        degraded = (sc.get("err")
                    or sc.get("title") in ("", "Amazon.in")
                    or (not sc.get("price") and not sc.get("rating")))
        if not degraded:
            sc["_degraded"] = False
            return sc
        time.sleep(5 + i * 5)
    sc["_degraded"] = True
    return sc


def main():
    args = sys.argv[1:]
    all_products = "--all" in args
    limit = 0
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])

    data = json.load(open("product.json", encoding="utf-8"))["products"]
    rows = []
    for i, p in enumerate(data):
        link = (p.get("link") or "").strip()
        if not link:
            continue
        if not all_products and i < 50:
            continue
        rows.append((i, p))
    if limit:
        rows = rows[:limit]

    print(f"QA {len(rows)} filled link(s) "
          f"({'all products' if all_products else 'new Diwali batch only'})\n")

    session = requests.Session()
    issues = []
    for n, (idx, p) in enumerate(rows, 1):
        card_name = p.get("name", "")
        card_price = int(re.sub(r"\D", "", str(p.get("price", "0"))) or 0)
        card_rating = float(p.get("rating") or 0)

        final_url, asin = resolve(session, p["link"])
        flags = []
        if final_url is None:
            flags.append(f"DEAD LINK ({asin})")
            actual_title = "-"
        elif asin is None:
            flags.append("NO ASIN in final URL")
            actual_title = final_url or "-"
        else:
            sc = scrape_retry(session, asin)
            if sc.get("_degraded"):
                flags.append("DEGRADED PAGE (Amazon bot check) — verify in browser")
                actual_title = sc.get("title") or "-"
            elif sc.get("err"):
                flags.append(sc["err"])
                actual_title = "-"
            else:
                actual_title = sc["title"] or "-"
                sim = jaccard(tokens(card_name), tokens(actual_title))
                if sim < 0.40:
                    flags.append(f"NAME MISMATCH (overlap {sim:.0%})")
                if not sc["in_stock"]:
                    flags.append("OUT OF STOCK?")
                if sc["price"]:
                    act = int(re.sub(r"\D", "", sc["price"]))
                    if card_price and abs(act - card_price) / card_price > 0.25:
                        flags.append(f"PRICE off: card {card_price} vs live {act}")
                else:
                    flags.append("no live price found (page may be degraded)")
                if sc["rating"] is not None and card_rating:
                    if abs(sc["rating"] - card_rating) >= 0.35:
                        flags.append(f"RATING off: card {card_rating} vs live {sc['rating']}")
                elif sc["rating"] is None:
                    flags.append("no rating scraped")

        status = "OK " if not flags else "!! "
        line = f"[{n:>2}/{len(rows)}] {status}#{idx} {card_name[:46]}"
        print(line)
        if flags:
            print(f"       -> {'; '.join(flags)}")
            print(f"       actual: {actual_title[:110]}")
            issues.append((idx, card_name, flags, actual_title))
        time.sleep(2.5)  # stay gentle with Amazon

    print(f"\n=== {len(issues)} of {len(rows)} need attention ===")
    for idx, name, flags, _ in issues:
        print(f"  #{idx} {name[:60]}")
        for f in flags:
            print(f"       - {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
