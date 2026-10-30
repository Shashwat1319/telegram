#!/usr/bin/env python3
"""Generate Pinterest-ready 1000x1500 deal cards from product.json
and optionally upload them to Pinterest boards via API v5.

Usage:
  python pin_post.py                 # generate cards for first 5 products -> pins/
  python pin_post.py 10              # generate first 10
  python pin_post.py 10 --upload     # generate first 10 AND upload to Pinterest
  python pin_post.py --upload 3      # upload only first 3 generated (skip rest)
  python pin_post.py --upload-all    # upload ALL cards already in pins/ not yet pinned

Upload picks board by product category (see BOARD_MAP). Token comes from
.env PINTEREST_ACCESS_TOKEN (saved by pinterest_boards.py).
"""
import json
import os
import re
import sys
from pathlib import Path

# Windows console (cp1252) can't encode ₹ / emoji — force UTF-8 for output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PRODUCTS = ROOT / "product.json"
OUT = ROOT / "pins"
STATE = ROOT / "pins_pinned.json"  # tracks uploaded pins to avoid dupes
FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_B = "C:/Windows/Fonts/arialbd.ttf"
FONT_HEAVY = "C:/Windows/Fonts/seguibl.ttf"
# Linux (GitHub Actions) fallbacks — DejaVu ships with ubuntu runners
FONT_L = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_LB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def F(kind, size):
    """Resolve a font that works on Windows (local) and Linux (CI)."""
    cands = {
        "regular": [FONT, FONT_L, "DejaVuSans.ttf"],
        "bold": [FONT_B, FONT_LB, "DejaVuSans-Bold.ttf"],
        "heavy": [FONT_HEAVY, FONT_LB, "DejaVuSans-Bold.ttf"],
    }[kind]
    for c in cands:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10
        return ImageFont.load_default()

BG_TOP = (229, 9, 20)
BG_BOT = (178, 7, 16)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 0)
GREEN = (6, 125, 61)
INK = (26, 26, 26)
CARD = (255, 255, 255)
GREY = (110, 110, 110)

SITE = "https://smartgahr.netlify.app/deals/"
API = "https://api.pinterest.com/v5"

# Category -> board name (must match boards created by pinterest_boards.py)
BOARD_MAP = {
    "Electronics": "Electronics Deals India — Earbuds & Gadgets",
    "Home & Kitchen": "Kitchen Finds India — Home & Kitchen Essentials",
    "Home Improvement": "Home Improvement & Electric Appliances India",
    "Beauty & Personal Care": "Amazon Deals Under Rs.999 India — Daily Loot Finds",
}
FALLBACK_BOARD = "Amazon Deals Under Rs.999 India — Daily Loot Finds"


def load_env():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k.startswith("PINTEREST_"):
            os.environ.setdefault(k, v)


def load_products():
    data = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    seen, out = set(), []
    for p in data.get("products", []):
        link = (p.get("link") or "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        out.append(p)
    return out


def wrap(draw, text, font, max_w):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def discount_num(p):
    try:
        return int(str(p.get("discount_percent") or "0").replace("%", "").strip() or 0)
    except ValueError:
        return 0


def card(p):
    """Vertical 1000x1500 Pinterest card (2:3 — Pinterest's preferred ratio)."""
    W, H = 1000, 1500
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(
            int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t),
            int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t),
            int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t),
        ))

    f_brand = F("bold", 56)
    f_tag = F("regular", 40)
    f_badge = F("heavy", 76)
    f_title = F("bold", 62)
    f_price = F("heavy", 132)
    f_mrp = F("regular", 58)
    f_fix = F("regular", 42)
    f_cta = F("bold", 48)

    # Brand header (tagline kept clear of badge zone)
    d.text((60, 64), "Smart", font=f_brand, fill=WHITE)
    w = d.textlength("Smart", font=f_brand)
    d.text((60 + w, 64), "Gahr", font=f_brand, fill=YELLOW)
    d.text((60, 136), "Deals under ₹999", font=f_tag,
           fill=(255, 235, 235))

    # Discount badge (top-right)
    disc = discount_num(p)
    if disc:
        bx = W - 60
        txt = f"{disc}% OFF"
        bb = d.textbbox((0, 0), txt, font=f_badge)
        tw = bb[2] - bb[0]
        badge_w = tw + 88
        d.rounded_rectangle([bx - badge_w, 60, bx, 60 + 136], radius=28,
                            fill=YELLOW)
        d.text((bx - badge_w / 2 - tw / 2, 76), txt, font=f_badge, fill=INK)

    # Main white card
    body_top = 300
    body_bot = 1180
    d.rounded_rectangle([48, body_top, W - 48, body_bot], radius=40, fill=CARD)

    # Title (up to 4 lines)
    title_lines = wrap(d, p.get("name", "Amazon Deal"), f_title, W - 200)
    y = body_top + 56
    for ln in title_lines[:4]:
        d.text((92, y), ln, font=f_title, fill=INK)
        y += 80

    # Price row
    y += 28
    price = str(p.get("price", "")).strip() or "₹?"
    mrp = str(p.get("mrp", "")).strip()
    d.text((92, y), price, font=f_price, fill=GREEN)
    pw = d.textlength(price, font=f_price)
    if mrp and mrp != price:
        d.text((116 + pw, y + 56), mrp, font=f_mrp, fill=GREY)
        mw = d.textlength(mrp, font=f_mrp)
        d.line([(118 + pw, y + 56 + 34), (118 + pw + mw, y + 56 + 34)],
               fill=GREY, width=5)
    y += 180

    # Rating (plain text — segoeui.ttf lacks emoji glyphs)
    rating = str(p.get("rating", "")).strip()
    if rating:
        d.text((92, y), f"{rating} / 5 rating", font=f_fix,
               fill=(70, 70, 70))
        y += 58

    # Fix / hook line
    fix = str(p.get("fix") or p.get("hook") or "").strip()
    if fix:
        for ln in wrap(d, fix, f_fix, W - 200)[:3]:
            d.text((92, y), ln, font=f_fix, fill=(70, 70, 70))
            y += 54

    # Category tag fills the empty card space + helps Pinterest context
    cat = str(p.get("category") or "").strip()
    if cat:
        y += 26
        f_cat = F("bold", 44)
        cat_txt = f"Category: {cat}"
        cw = d.textlength(cat_txt, font=f_cat)
        d.rounded_rectangle([92, y, 92 + cw + 56, y + 76], radius=38,
                            fill=(255, 240, 240))
        d.text((120, y + 16), cat_txt, font=f_cat, fill=BG_TOP)
        y += 76

    # CTA footer
    d.rounded_rectangle([48, 1230, W - 48, 1420], radius=32, fill=WHITE)
    d.text((92, 1272), "Grab this deal →", font=f_cta, fill=BG_TOP)
    d.text((92, 1338), "smartgahr.netlify.app — new deals daily", font=f_fix,
           fill=GREY)
    return img


def slug(p, i):
    name = re.sub(r"[^a-z0-9]+", "_", str(p.get("name", "")).lower()).strip("_")[:40]
    return f"pin_{i:02d}_{name}.png"


def generate(n):
    prods = load_products()[:n]
    OUT.mkdir(exist_ok=True)
    saved = []
    for i, p in enumerate(prods, 1):
        path = OUT / slug(p, i)
        card(p).save(path, "PNG")
        saved.append((path, p))
        print("saved", path.name)
    return saved


# ---------------- Pinterest upload ----------------

def load_pinned():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_pinned(st):
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")


def get_boards(h):
    import requests
    r = requests.get(f"{API}/boards", params={"page_size": 100}, headers=h,
                     timeout=30)
    if r.status_code != 200:
        print(f"GET /boards failed: HTTP {r.status_code} {r.text[:200]}")
        return {}
    return {b["name"]: b["id"] for b in r.json().get("items", [])}


def upload(items, limit=None):
    import requests
    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        print("PINTEREST_ACCESS_TOKEN missing — pehle py pinterest_boards.py chala.")
        return
    h = {"Authorization": f"Bearer {token}"}
    boards = get_boards(h)
    if not boards:
        return
    pinned = load_pinned()
    done = 0

    for path, p in items:
        if limit is not None and done >= limit:
            print(f"daily quota reached ({limit} pins)")
            break
        key = str(p.get("link", ""))
        if key in pinned:
            print(f"skip (already pinned): {path.name}")
            continue
        cat = p.get("category") or ""
        board_name = BOARD_MAP.get(cat, FALLBACK_BOARD)
        board_id = boards.get(board_name) or boards.get(FALLBACK_BOARD)
        if not board_id:
            print(f"FAIL: no board found for '{board_name}'")
            continue

        title = f"{p.get('name','Amazon Deal')} — {p.get('price','')} ({p.get('discount_percent','')} off)"
        title = title[:95]  # Pinterest title cap ~100
        desc = (f"{p.get('fix') or p.get('hook','')} "
                f"MRP {p.get('mrp','')} → {p.get('price','')} "
                f"({p.get('discount_percent','')} off, ⭐{p.get('rating','')}/5). "
                f"Verified Amazon India deal under ₹999. More daily deals: "
                f"smartgahr.netlify.app")[:480]

        # Pinterest API needs a public image URL — use image_url upload
        # via multipart: source_type=image_base64 alternative; simplest is
        # base64 from local file.
        import base64
        b64 = base64.b64encode(path.read_bytes()).decode()
        r = requests.post(
            f"{API}/pins", headers=h, timeout=60,
            json={
                "board_id": board_id,
                "title": title,
                "description": desc,
                "link": SITE,
                "media_source": {
                    "source_type": "image_base64",
                    "content_type": "image/png",
                    "data": b64,
                },
            },
        )
        if r.status_code in (200, 201):
            pid = r.json().get("id")
            pinned[key] = pid
            save_pinned(pinned)
            done += 1
            print(f"PINNED -> {board_name}: {title[:60]} ({pid})")
        else:
            print(f"FAIL: {path.name} — HTTP {r.status_code} {r.text[:250]}")
    print(f"uploaded {done} pin(s) this run")


def main():
    load_env()
    args = sys.argv[1:]

    daily = None
    if "--daily" in args:
        idx = args.index("--daily")
        daily = int(args[idx + 1]) if idx + 1 < len(args) and args[idx + 1].isdigit() else 2

    upload_all = "--upload-all" in args
    do_upload = "--upload" in args or upload_all or daily is not None
    nums = [a for a in args if a.isdigit() and a != (str(daily) if daily else "")]
    n = int(nums[0]) if nums else (999 if (upload_all or daily) else 5)

    if upload_all or daily is not None:
        # Full catalogue so unpinned deals anywhere in the list get picked
        OUT.mkdir(exist_ok=True)
        items = []
        prods = load_products()
        for i, p in enumerate(prods, 1):
            path = OUT / slug(p, i)
            if not path.exists():
                path.parent.mkdir(exist_ok=True)
                card(p).save(path, "PNG")
            items.append((path, p))
        print(f"{len(items)} cards ready in pins/")
    else:
        items = generate(n)

    if do_upload:
        print("\n--- Uploading to Pinterest ---")
        upload(items, limit=daily)


if __name__ == "__main__":
    main()
