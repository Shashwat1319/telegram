"""Generate a weekly SEO article draft (Dev.to / Medium) from the week's top deals.

Pulls the highest-discount products from content_home.json, content_ht.json
and content_bdia.json, dedupes by name, and writes a ready-to-paste markdown
draft into seo_drafts/ with every product link routed through the tracker
(src=seo) so clicks are attributable.

Usage:
    py seo_weekly.py                  # draft from all sources, top 10
    py seo_weekly.py --top 15         # more deals
    py seo_weekly.py --sources ht,home
    py seo_weekly.py --week 2026-W43  # label in filename (default: current ISO week)
"""

import argparse
import json
import logging
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("seo_weekly")

OUT_DIR = "seo_drafts"
SOURCE_FILES = {
    "home": "content_home.json",
    "ht": "content_ht.json",
    "bdia": "content_bdia.json",
}


def _load_products(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("products") or data.get("items") or []
        return data or []
    except Exception as e:
        log.warning("Could not read %s: %s", path, e)
        return []


def _name(p):
    return str(p.get("name") or p.get("title") or "").strip()


def _discount(p):
    """Best-effort discount %: explicit field, or price/mrp arithmetic."""
    for key in ("discount", "discount_val", "discount_pct", "drop"):
        v = p.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
        if isinstance(v, str):
            m = re.search(r"(\d+)", v)
            if m:
                return int(m.group(1))
    try:
        price = float(re.sub(r"[^\d.]", "", str(p.get("price", ""))))
        mrp = float(re.sub(r"[^\d.]", "", str(p.get("mrp", ""))))
        if mrp > 0 and price < mrp:
            return int((1 - price / mrp) * 100)
    except Exception:
        pass
    return 0


def _price_int(p):
    try:
        return int(float(re.sub(r"[^\d.]", "", str(p.get("price", "")))))
    except Exception:
        return 0


def _tracked(url, product, src="seo"):
    tag = os.getenv("AFFILIATE_ID_IN", "shashwat022-21")
    tracker = os.getenv("CLICK_TRACKER_URL", "").strip()
    if not url:
        return None
    if "tag=" in url:
        direct = url
    else:
        sep = "&" if "?" in url else "?"
        direct = f"{url}{sep}tag={tag}"
    if not tracker:
        return direct
    out = f"{tracker}/go?url={quote(direct)}"
    pid = product.get("id") or re.sub(r"[^a-z0-9]+", "-", str(product.get("name", "")).lower()).strip("-")[:60] or "unknown"
    out += f"&product={quote(str(pid)[:60])}"
    out += f"&title={quote(str(product.get('name', ''))[:80])}"
    out += f"&src={quote(src)}"
    return out


def build_draft(products, week_label, top_n):
    now = datetime.now(timezone.utc)
    ranked = sorted(products, key=lambda p: (-_discount(p), _price_int(p)))
    picked = ranked[:top_n]

    lines = [
        f"# Best Amazon Deals This Week ({week_label}) — Up to {picked[0]['_disc']}% Off",
        "",
        f"*Updated {now.strftime('%d %b %Y')}. Prices change fast — click through for the live price.*",
        "",
    ]
    for i, p in enumerate(picked, 1):
        name = p.get("_clean_name") or _name(p) or "Deal"
        price = p.get("price", "?")
        mrp = p.get("mrp", "")
        disc = p["_disc"]
        fix = str(p.get("fix") or p.get("body") or "").strip()
        link = p.get("_link")
        lines.append(f"## {i}. {name[:80]}")
        lines.append("")
        if mrp:
            lines.append(f"**{mrp} → {price}** ({disc}% off)")
        else:
            lines.append(f"**{price}** ({disc}% off)")
        lines.append("")
        if fix:
            # body contains markdown emphasis — take first lines only
            snippet = " ".join(fix.splitlines()[:2])[:200]
            lines.append(snippet)
            lines.append("")
        if link:
            lines.append(f"[Check latest price →]({link})")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines += [
        "## How we pick these",
        "",
        "Every deal above is verified: real price drop, real MRP, no fake urgency. "
        "We track price history daily and drop anything that inflates its MRP.",
        "",
        "Want these deals in Telegram before they hit the article? "
        "Join [@smartgahr](https://t.me/smartgahr) — daily price-drop alerts, free.",
        "",
        f"*Disclaimer: prices and availability are set by Amazon and can change "
        f"at any time. As an Amazon Associate we earn from qualifying purchases.*",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--sources", default="home,ht,bdia", help="comma list: home,ht,bdia")
    ap.add_argument("--week", default=None, help="label, e.g. 2026-W43 (default: current ISO week)")
    args = ap.parse_args()

    week_label = args.week or datetime.now(timezone.utc).strftime("IW%G-W%V")
    wanted = [s.strip() for s in args.sources.split(",") if s.strip() in SOURCE_FILES]

    seen = set()
    products = []
    for src in wanted:
        for p in _load_products(SOURCE_FILES[src]):
            # Same product is stored once per promo format ("— Deal Alert",
            # "— 💡 Problem Solved", ...) — dedupe on product_id, then link.
            key = (
                str(p.get("product_id") or "").strip()
                or str(p.get("link") or "").strip()
                or _name(p).split(" — ")[0].strip().lower()
            )
            if not key or key in seen:
                continue
            if _discount(p) < 40:
                continue
            seen.add(key)
            q = dict(p)
            q["_disc"] = _discount(p)
            q["_link"] = _tracked(p.get("link", ""), p)
            q["_clean_name"] = _name(p).split(" — ")[0].strip()
            if q["_link"]:
                products.append(q)

    if not products:
        log.error("No products with >=40%% discount found in %s", wanted)
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    fname = os.path.join(OUT_DIR, f"deals_{week_label}.md")
    md = build_draft(products, week_label, args.top)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(md)
    log.info("Draft written: %s (%d products in, top %d used)", fname, len(products), min(args.top, len(products)))
    log.info("Paste into Dev.to/Medium after a quick human read; links carry src=seo.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
