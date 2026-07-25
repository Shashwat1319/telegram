import os
import sys
import logging
import re
from datetime import datetime
from data import load_json, save_json

log = logging.getLogger("feeder")

PRODUCT_FILE = "product_home.json"
CONTENT_FILE = "content_home.json"


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def calc_discount(price_str, mrp_str):
    try:
        p = float(re.sub(r"[^\d.]", "", str(price_str)))
        m = float(re.sub(r"[^\d.]", "", str(mrp_str)))
        if m > 0 and p < m:
            return int((1 - p / m) * 100)
    except Exception:
        pass
    return 0


def clean_product_file(source=None):
    path = source or PRODUCT_FILE
    raw = load_json(path, default={"products": []})
    prods = raw.get("products", [])
    if not prods:
        return []
    valid = [p for p in prods if p.get("link")]
    log.info("Loaded %s: %d valid products found", path, len(valid))
    return valid


CONTENT_FORMATS = ["pain_fix", "deal_alert", "short_urgency"]

HINGLISH_CTA = "लो लो ⚡ Limited stock hai — jaldi karo!"
HINGLISH_HOOKS = [
    f"🔥 {HINGLISH_CTA}",
    f"⚡ Ghar ke liye best deal! {HINGLISH_CTA}",
    f"🏡 Ghar ka budget bachao! {HINGLISH_CTA}",
]

def _body_pain_fix(prod):
    pain = prod.get("pain", "")
    fix = prod.get("fix", "")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    hook = prod.get("hook", "Grab this deal!")
    import random
    parts = []
    if pain:
        parts.append(f"😣 {pain}")
    if fix:
        parts.append(f"✅ {fix}")
    if price and mrp:
        parts.append(f"💰 ~~{mrp}~~ → **{price}** ({disc} OFF)")
    elif price:
        parts.append(f"💰 **{price}**")
    parts.append(random.choice(HINGLISH_HOOKS))
    return "\n\n".join(parts)

def _body_deal_alert(prod):
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    rating = prod.get("rating", "4.5★")
    parts = [f"⚡ FLAT {disc} OFF! Ghar ke liye best deal!"]
    parts.append(f"⭐ {rating}/5 Rating")
    if price and mrp:
        parts.append(f"💰 ~~{mrp}~~ → **{price}**")
    elif price:
        parts.append(f"💰 **{price}**")
    import random
    parts.append(random.choice(HINGLISH_HOOKS))
    return "\n\n".join(parts)

def _body_short_urgency(prod):
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    hook = prod.get("hook", "")
    import random
    parts = [f"🚨 Sasta deal alert!\n{name}"]
    if price and mrp:
        parts.append(f"💰 ~~{mrp}~~ → **{price}** (Bachao {disc})")
    elif price:
        parts.append(f"💰 **{price}**")
    parts.append(random.choice(HINGLISH_HOOKS))
    return "\n\n".join(parts)

_FORMATTERS = {
    "pain_fix": _body_pain_fix,
    "deal_alert": _body_deal_alert,
    "short_urgency": _body_short_urgency,
}

def to_content_items(prod):
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    if not disc and price and mrp:
        calculated = calc_discount(price, mrp)
        if calculated > 0:
            disc = f"{calculated}%"
    link = prod.get("link", "")
    img = prod.get("image", "")
    cat = prod.get("category", "Deals")
    rating = prod.get("rating", "")
    disc_val = calc_discount(price, mrp)
    is_loot = disc_val >= 40
    base_id = slugify(name)

    items = []
    for fmt in CONTENT_FORMATS:
        formatter = _FORMATTERS[fmt]
        body = formatter(prod)
        items.append({
            "id": f"{base_id}-{fmt}" if base_id else f"prod-{fmt}-{hash(name) % 10000}",
            "title": name[:90],
            "body": body,
            "format": fmt,
            "price": price,
            "mrp": mrp,
            "discount": str(disc),
            "discount_val": disc_val,
            "is_loot": is_loot,
            "link": link,
            "image": img,
            "category": cat,
            "rating": str(rating),
            "product_id": base_id,
            "hook": prod.get("hook", ""),
            "pain": prod.get("pain", ""),
            "fix": prod.get("fix", ""),
        })
    return items


def merge_posted_history(output_path=None):
    old_file = "posted_products.json"
    new_file = (output_path or CONTENT_FILE).replace(".json", "_posted.json")

    if not os.path.exists(old_file):
        return

    old = load_json(old_file, default={})
    new = load_json(new_file, default={})

    merged = dict(new)
    for title, data in old.items():
        if title not in merged:
            count = data.get("count", data.get("posted_count", 1))
            merged[title] = {
                "last": data.get("last", data.get("last_posted", datetime.now().isoformat())),
                "count": count,
            }

    save_json(new_file, merged)


def feed(limit=100, source=None, output=None):
    products = clean_product_file(source=source)
    if not products:
        log.warning("No valid products found")
        return

    all_items = []
    for p in products[:limit]:
        all_items.extend(to_content_items(p))
    all_items.sort(key=lambda x: x.get("discount_val", 0), reverse=True)

    out_path = output or CONTENT_FILE
    content = {"items": all_items}
    save_json(out_path, content)
    log.info("Generated %d content items from %d products (%d variants each) → %s",
             len(all_items), min(len(products), limit), len(CONTENT_FORMATS), out_path)

    merge_posted_history(output_path=out_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate content items from product file")
    parser.add_argument("--source", default=PRODUCT_FILE, help="Product JSON file (default: product.json)")
    parser.add_argument("--output", default=CONTENT_FILE, help="Output content JSON file (default: content.json)")
    parser.add_argument("--limit", type=int, default=100, help="Max products to process")
    args = parser.parse_args()
    feed(limit=args.limit, source=args.source, output=args.output)
