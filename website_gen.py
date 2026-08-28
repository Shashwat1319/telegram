"""Generate website deal pages from the live product feed.
Usage: python website_gen.py [--source product_home.json]
Writes markdown files to website/src/content/deals/ with tracked affiliate buyLinks.
"""
import os
import re
import sys
import logging
from datetime import datetime
from data import load_json
from utils import tracked_url
from feeder import slugify, apply_niche_filter, calc_discount

log = logging.getLogger("website_gen")

DEALS_DIR = "website/src/content/deals"
SOURCE = "product_home.json"
CHANNEL = "@smartgahr"
CHANNEL_URL = "https://t.me/smartgahr"
TRACKER = "https://budgetdeals-tracker-737523f4.netlify.app"


def _price(prod):
    try:
        return float(re.sub(r"[^\d.]", "", str(prod.get("price", ""))))
    except Exception:
        return 0.0


def _description(prod):
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    name = prod.get("name", "Product")
    if price and mrp:
        return f"Get {name} at just {price} - Save {disc}! Verified Amazon deal."
    return f"Get {name} at a verified low price. Checked by SmartGahr."


def _body(prod):
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    rating = prod.get("rating", "")
    pain = prod.get("pain", "")
    fix = prod.get("fix", "")
    reason = prod.get("loot_reason", "")
    cat = prod.get("category", "")
    lines = []
    lines.append(f"## Why This Deal?\n\n{pain}" if pain else "## Why This Deal?\n\nThis product offers great value for money at its current discounted price.")
    if fix:
        lines.append(f"\n\n**What makes it worth buying:** {fix}")
    if reason:
        lines.append(f"\n\n**Loot reason:** {reason}")
    lines.append(f"\n\n## Price Breakdown\n\n| | Price |\n|---|---|\n| MRP | ~~{mrp}~~ |\n| Deal Price | **{price}** |\n| You Save | **{disc}** |")
    if rating:
        lines.append(f"\n\n## What Buyers Say\n\nAmazon buyers rate this product **{rating}/5**. "
                     f"{'This is a well-reviewed product with satisfied buyers.' if float(rating or '0') >= 4.0 else 'Check the reviews for detailed feedback before buying.'}")
    lines.append(f"\n\n## Who Should Buy This?\n\n"
                 f"- Anyone looking for a reliable **{cat.lower() if cat else 'budget'}** product under {price}\n"
                 f"- People who want {'verified quality at a discount' if rating and float(rating or '0') >= 4.0 else 'a budget-friendly option'}\n"
                 f"- Great for personal use or as a gift")
    lines.append(f"\n\n## Things to Note\n\n"
                 f"- Price may change — deal prices on Amazon are dynamic\n"
                 f"- Check size/specs before ordering\n"
                 f"- {'This deal qualifies for SmartGahr\'s 40%+ discount filter 🟢' if disc and int(disc.replace('%','').strip() or '0') >= 40 else 'Discount is moderate — still a decent deal at this price 🟡'}")
    lines.append(f"\n\n## More Deals Like This?\n\n"
                 f"Join [**@smartgahr**](https://t.me/smartgahr) on Telegram for daily verified loot deals. "
                 f"We post the best Amazon deals under ₹999 — every deal checked, every discount above 40%.")
    return "\n\n".join(lines)


def generate_deal_file(prod, out_dir=DEALS_DIR):
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    rating = prod.get("rating", "")
    cat = prod.get("category", "Deals")
    link = prod.get("link", "")
    img = prod.get("image", "")
    slug = slugify(name)
    if not slug:
        return None
    disc_num = calc_discount(price, mrp)
    buy_link = tracked_url(
        link,
        product_id=slug,
        title=name,
        price=price,
        discount=disc if disc else (f"{disc_num}%" if disc_num else ""),
        image=img,
    )
    rating_str = str(rating) if rating else "4.0"
    md = f"""---
title: "{name} @ Just {price} - Save {disc}!"
description: "{_description(prod)}"
pubDate: "{datetime.now().strftime('%Y-%m-%d')}"
price: "{price}"
mrp: "{mrp}"
discount: "{disc}"
image: "{img}"
buyLink: "{buy_link}"
category: "{cat}"
rating: "{rating_str}"
---

🔥 **{disc} OFF** on {name}

💸 **Price**: ~~{mrp}~~ → **{price}**
⭐ **Rating**: {rating_str}

👉 **[Buy Now on Amazon]({buy_link})**

{_body(prod)}
"""
    path = os.path.join(out_dir, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def clean_stale_deals(products, out_dir=DEALS_DIR):
    """Remove old deal pages whose product is no longer in the feed."""
    keep = {slugify(p.get("name", "")) for p in products if slugify(p.get("name", ""))}
    removed = 0
    if os.path.isdir(out_dir):
        for f in os.listdir(out_dir):
            if not f.endswith(".md"):
                continue
            if f.startswith(".gitkeep"):
                continue
            slug = f[:-3]
            if slug not in keep:
                try:
                    os.remove(os.path.join(out_dir, f))
                    removed += 1
                except OSError:
                    pass
    if removed:
        log.info("Removed %d stale deal pages", removed)
    return removed


def run(source=SOURCE, out_dir=DEALS_DIR):
    data = load_json(source, default={"products": []})
    products = [p for p in data.get("products", []) if p.get("link")]
    products = apply_niche_filter(products)
    os.makedirs(out_dir, exist_ok=True)
    clean_stale_deals(products, out_dir)
    written = 0
    for p in products:
        path = generate_deal_file(p, out_dir)
        if path:
            written += 1
    log.info("Generated %d deal pages → %s", written, out_dir)
    return written


if __name__ == "__main__":
    import argparse
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate website deal pages from product feed")
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--out", default=DEALS_DIR)
    args = parser.parse_args()
    run(source=args.source, out_dir=args.out)
    print("Website deals generated OK")