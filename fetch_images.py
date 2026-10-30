#!/usr/bin/env python3
"""Resolve affiliate links to ASINs and download product images locally.

How it works (no scraping, no API key, no bot-wall fights):
  1. amzn.to link  -> 301 Location  ->  https://www.amazon.in/<slug>/dp/<ASIN>
  2. image URL     ->  https://m.media-amazon.com/images/P/<ASIN>.01._SCLZZZZZZZ_.jpg
     (Amazon's public image CDN — the same pattern the old affiliate widgets used;
      it answers plain requests even when the HTML product page is bot-walled)
  3. download to netlify-redirector/img/<ASIN>.jpg  (local = fast, indexable, no hotlink)

State is kept in product_images.json  ->  { "<affiliate link>": {"asin": ..., "file": ...} }
_site_builder.py merges that at build time, so product.json stays owned by the
laptop pipeline and images survive every product refresh.

Usage:
  py fetch_images.py              # fill missing images
  py fetch_images.py --limit 5    # test run
  py fetch_images.py --force      # refetch everything
  py fetch_images.py --delay 1.5  # seconds between requests
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
PRODUCTS_FILE = ROOT / "product.json"
IMAGES_FILE = ROOT / "product_images.json"
IMG_DIR = ROOT / "netlify-redirector" / "img"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"}

ASIN_IN_URL = re.compile(r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})", re.I)
ASIN_IN_IMAGE = re.compile(r"/images/P/([A-Z0-9]{10})\.")


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        print(f"! could not read {path.name}: {e}")
        return default


def save_images(images):
    IMAGES_FILE.write_text(
        json.dumps(images, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_products():
    data = load_json(PRODUCTS_FILE, {})
    return data.get("products", data if isinstance(data, list) else [])


def resolve_asin(session, link, attempts=3):
    """Follow the short link just far enough to read the ASIN from the Location header."""
    last = ""
    for attempt in range(attempts):
        try:
            r = session.get(link, headers=HEADERS, timeout=30, allow_redirects=True)
        except requests.RequestException as e:
            last = f"{type(e).__name__}"
            time.sleep(2 + attempt * 2)
            continue

        for candidate in (r.url, r.headers.get("Location", "")):
            m = ASIN_IN_URL.search(candidate or "")
            if m:
                return m.group(1).upper(), candidate
        final = r.url or ""
        m = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", final)
        return (m.group(1).upper() if m else None), final
    return None, last


# Amazon answers 200 with a 43-byte transparent GIF when an ASIN has no legacy
# "P/" image entry. Trying several size variants costs one request each and
# catches the rare ASIN that only has one of them.
IMAGE_VARIANTS = [
    "https://m.media-amazon.com/images/P/{a}.01._SCLZZZZZZZ_.jpg",
    "https://m.media-amazon.com/images/P/{a}.01._SCLZZZZZZZ_SX500_.jpg",
    "https://m.media-amazon.com/images/P/{a}.01.LZZZZZZZ.jpg",
]


def download_image(session, asin, dest_dir):
    notes = []
    for variant in IMAGE_VARIANTS:
        url = variant.format(a=asin)
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            notes.append(f"{type(e).__name__}")
            continue
        if r.status_code != 200:
            notes.append(f"HTTP {r.status_code}")
            continue
        data = r.content
        if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG")):
            notes.append("placeholder/not image")
            continue
        if len(data) < 2500:
            notes.append(f"too small ({len(data)}B)")
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"{asin}.jpg"
        path.write_bytes(data)
        return f"img/{asin}.jpg", f"{len(data) // 1024} KB"
    return None, ", ".join(notes) or "no image"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    products = load_products()
    images = load_json(IMAGES_FILE, {})
    if not isinstance(images, dict):
        images = {}

    todo = []
    for p in products:
        link = (p.get("link") or "").strip()
        if not link:
            continue
        entry = images.get(link)
        has_file = bool(entry and (ROOT / "netlify-redirector" / entry.get("file", "")).exists())
        if not args.force and has_file:
            continue
        todo.append(p)

    if args.limit:
        todo = todo[: args.limit]

    print(f"products={len(products)} cached={sum(1 for v in images.values() if v)} to_fetch={len(todo)}")
    if not todo:
        print("nothing to do")
        return 0

    session = requests.Session()
    ok = fail = 0
    failures = []

    for i, p in enumerate(todo, 1):
        link = (p.get("link") or "").strip()
        name = (p.get("name") or "")[:50]
        asin, final_url = resolve_asin(session, link)
        if not asin:
            fail += 1
            failures.append((name, "no ASIN", final_url[:70]))
            print(f"[{i}/{len(todo)}] FAIL {name} | no ASIN in {final_url[:60]}")
            time.sleep(args.delay)
            continue

        file_rel, note = download_image(session, asin, IMG_DIR)
        if file_rel:
            images[link] = {"asin": asin, "file": file_rel}
            save_images(images)
            ok += 1
            print(f"[{i}/{len(todo)}] OK   {name} | {asin} | {note}")
        else:
            fail += 1
            failures.append((name, note, asin))
            print(f"[{i}/{len(todo)}] FAIL {name} | {asin} | {note}")

        if i < len(todo):
            time.sleep(args.delay + random.uniform(0, 0.8))

    print(f"\ndone: ok={ok} fail={fail} cached={len(images)} -> {IMAGES_FILE.name}")
    if failures:
        print("\nfailures:")
        for name, why, extra in failures:
            print(f"  - {name}: {why} ({extra})")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
