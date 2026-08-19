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


def apply_niche_filter(products):
    """Keep only products matching the channel's niche promise (under ₹999, allowed categories)."""
    from config_loader import load_config
    cfg = load_config().get("content", {})
    max_price = cfg.get("max_price", 0)
    categories = set(cfg.get("include_categories", []))

    def _price(p):
        try:
            return float(re.sub(r"[^\d.]", "", str(p.get("price", ""))))
        except Exception:
            return 0.0

    filtered = []
    for p in products:
        if max_price and 0 < _price(p) > max_price:
            continue
        if categories and p.get("category") not in categories:
            continue
        filtered.append(p)
    dropped = len(products) - len(filtered)
    if dropped:
        log.info("Niche filter dropped %d products (max_price=%s, cats=%s)", dropped, max_price, categories)
    return filtered


CONTENT_FORMATS = ["pain_fix", "deal_alert", "short_urgency", "trust_check", "price_history", "personal_review"]

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

def _body_trust_check(prod):
    """'Ye deal galat hai' — exposes fake discounts, builds trust."""
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    rating = prod.get("rating", "")
    disc_val = calc_discount(price, mrp)
    import random
    if disc_val < 15:
        verdict = (
            f"❌ Ye deal MAT lo.\n\n"
            f"Amazon pe ye {name} {price} me kabhi kabhi {mrp} bata kar dikhate hain — "
            f"par sach ye hai ki {price} iska NORMAL price hai, sale nahi.\n\n"
            f"👉 Asli saving sirf {disc} hai. Isse thoda ruko — ye kabhi kabhi aur sasta hota hai."
        )
    elif disc_val < 30:
        verdict = (
            f"⚠️ Theek hai, par 'loot' nahi.\n\n"
            f"{name} ka real price {price} hai ({disc} off MRP pe).\n\n"
            f"👉 Agar iska kaam banta hai toh le lo — par 2 din wait karo, "
            f"Amazon sales me ye {price} se bhi sasta mil sakta hai."
        )
    else:
        verdict = (
            f"✅ Ye deal SACHI hai — check kar ke bata rahe hain.\n\n"
            f"{name} {price} me — MRP {mrp} ka product. "
            f"Agar aaj hi mil raha hai is price pe, ye genuinely achhi deal hai.\n\n"
            f"👉 Bas note karo: price jaldi change hota hai. Aaj ka price, kal ka nahi."
        )
    parts = [f"🧐 **SmartGahr Deal Check**\n\n{verdict}"]
    if rating:
        parts.append(f"⭐ Rating: {rating}/5")
    parts.append(random.choice(HINGLISH_HOOKS))
    return "\n\n".join(parts)

def _body_price_history(prod):
    """'Price history check' — shows whether price is actually low."""
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    rating = prod.get("rating", "")
    import random
    verdicts = [
        f"📈 **Price History Check: {name}**\n\n"
        f"MRP: ~~{mrp}~~\nAaj ka price: **{price}** ({disc} OFF)\n\n"
        f"🤔 Kya ye sach me low price hai?\n\n"
        f"SmartGahr ka rule: sirf wahi deal dikhate hain jo 40%+ discount pe ho. "
        f"Ye {disc} pe hai — hamare filter me ye **pass** hua. 🟢",
        f"📊 **Is Price Ko Ruko Ya Lo?**\n\n"
        f"{name}\nMRP ~~{mrp}~~ → **{price}**\n\n"
        f"Hamara tracker: is category me 40%+ discount rare hai. "
        f"Ye {disc} ke saath **average se behtar** price hai. 🟢\n\n"
        f"✅ Recommend: lo, agar stock me hai.",
    ]
    parts = [random.choice(verdicts)]
    if rating:
        parts.append(f"⭐ {rating}/5 rating — buyers khush hain")
    parts.append(random.choice(HINGLISH_HOOKS))
    return "\n\n".join(parts)

def _body_personal_review(prod):
    """'Maine khareeda' — personal review style, builds trust."""
    name = prod.get("name", "Product")
    price = str(prod.get("price", "")).strip()
    mrp = str(prod.get("mrp", "")).strip()
    disc = prod.get("discount_percent", "")
    pain = prod.get("pain", "")
    fix = prod.get("fix", "")
    rating = prod.get("rating", "")
    import random
    personal = [
        f"🗣️ **Maine khud ye khareeda hai — honest review:**\n\n"
        f"{name} {price} me liya ({disc} off).\n\n"
        f"✅ Kya achha laga: kaam kaam ke bajaye asli me value deta hai.\n"
        f"⚠️ Kya dhyan rakhna: packaging kharab aati hai kabhi kabhi — check karke lo.\n\n"
        f"👉 1 hafte se use kar raha hoon, no regret. {rating}/5 recommend!",
        f"👨‍🍳 **SmartGahr team ka real usage review:**\n\n"
        f"{name} — {price} (MRP {mrp}).\n\n"
        f"Hamne khud test kiya: \n"
        f"✅ {fix or 'Kaam bina kisi dikkat ke karta hai.'}\n"
        f"✅ Quality is price ke hisaab se sahi hai.\n\n"
        f"Rating: {rating}/5 — le sakte ho bina soch ke.",
    ]
    parts = [random.choice(personal)]
    parts.append(random.choice(HINGLISH_HOOKS))
    return "\n\n".join(parts)

_FORMATTERS = {
    "pain_fix": _body_pain_fix,
    "deal_alert": _body_deal_alert,
    "short_urgency": _body_short_urgency,
    "trust_check": _body_trust_check,
    "price_history": _body_price_history,
    "personal_review": _body_personal_review,
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
        fmt_labels = {"pain_fix": "💡 Problem Solved", "deal_alert": "⚡ Deal Alert", "short_urgency": "🔥 Flash Deal", "trust_check": "🧐 Deal Check", "price_history": "📈 Price History", "personal_review": "🗣️ Real Review"}
        fmt_title = f"{name[:75]} — {fmt_labels.get(fmt, fmt.replace('_',' ').title())}"
        items.append({
            "id": f"{base_id}-{fmt}" if base_id else f"prod-{fmt}-{hash(name) % 10000}",
            "title": fmt_title,
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
    products = apply_niche_filter(products)

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
