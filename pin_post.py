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
import hashlib
import json
import math
import os
import random
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
STATUS = ROOT / "pinterest_status.json"  # last run report (committed by CI)
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
ORIGIN = "https://smartgahr.netlify.app/"
API = "https://api.pinterest.com/v5"

# affiliate link -> product page path (deep links convert far better than the
# generic /deals/ homepage; built lazily from _site_builder so URLs always match
# the pages the site actually generates). Any failure = fallback to SITE.
_PATH_MAP = None


def product_page_url(p):
    global _PATH_MAP
    if _PATH_MAP is None:
        try:
            from _site_builder import assign_product_paths, load_products as _sb_products, PRODUCT_PATHS
            assign_product_paths(_sb_products())
            _PATH_MAP = dict(PRODUCT_PATHS)
        except Exception:
            _PATH_MAP = {}
    rel = _PATH_MAP.get((p.get("link") or "").strip())
    return (ORIGIN + rel) if rel else SITE

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


def price_num(p):
    try:
        return float(re.sub(r"[^\d.]", "", str(p.get("price", ""))) or 0)
    except ValueError:
        return 0.0


def commission_score(p):
    """Expected-commission proxy: higher price = bigger payout per sale;
    discount adds buying intent. Pin highest-score deals first."""
    return price_num(p) * (1 + discount_num(p) / 100.0)


def card_v1(p):
    """DEPRECATED (kept for reference) — flat red gradient design, 2026-10 era.
    Pinterest got 70 pins from this; v2 ('Luxe BF') below replaces it."""
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


def star_poly(cx, cy, r_out, r_in, points=5, rot=-90):
    """Polygon points for a symmetric star (rot=-90 puts a point straight up)."""
    pts = []
    for i in range(points * 2):
        ang = math.radians(rot + i * 180.0 / points)
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def card(p):
    """v2 'Luxe BF' Pinterest card (1000x1500, 2:3).

    Dark charcoal + gold frame, white product card, red starburst discount,
    gold CTA pill, deterministic confetti (same product = same art).
    Designed for the Black Friday search wave: BF branding in-image AND in
    the pin title/description (see upload()).
    """
    W, H = 1000, 1500

    # --- background: charcoal -> warm charcoal vertical gradient ---
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    top, bot = (15, 15, 19), (41, 34, 26)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(
            int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))

    # --- deterministic bokeh rings + confetti dots ---
    seed = sum(ord(c) for c in str(p.get("link") or p.get("name") or "deal"))
    rnd = random.Random(seed)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for i in range(7):
        cx, cy = rnd.randint(0, W), rnd.randint(0, H)
        r = rnd.randint(45, 150)
        col = (212, 175, 55, 16) if i % 2 else (229, 9, 20, 14)
        od.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=3)
    for _ in range(16):
        x, y, r = rnd.randint(40, W - 40), rnd.randint(40, H - 40), rnd.randint(3, 7)
        od.ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 0, 42))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)

    # thin gold frame
    d.rounded_rectangle([26, 26, W - 26, H - 26], radius=52,
                        outline=(212, 175, 55), width=4)

    # --- header ---
    f_brand = F("bold", 58)
    d.text((64, 62), "Smart", font=f_brand, fill=WHITE)
    w = d.textlength("Smart", font=f_brand)
    d.text((64 + w, 62), "Gahr", font=f_brand, fill=YELLOW)
    d.text((64, 136), "Black Friday 2026 · handpicked deals",
           font=F("regular", 34), fill=(195, 195, 195))
    f_pill = F("bold", 40)
    pt = "BF 2026"
    pw = d.textlength(pt, font=f_pill)
    d.rounded_rectangle([W - 64 - pw - 64, 62, W - 64, 134],
                        radius=36, fill=(229, 9, 20))
    d.text((W - 64 - pw - 32, 74), pt, font=f_pill, fill=WHITE)

    # --- product card with soft shadow ---
    ct, cb = 300, 1170
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([68, 318, 956, 1190], radius=46, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img.convert("RGBA"), sh).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([56, ct, W - 56, cb], radius=46, fill=CARD)

    # --- discount starburst (sits on the card's top-right corner) ---
    disc = discount_num(p)
    if disc:
        cx, cy = 852, 332
        d.polygon(star_poly(cx, cy, 132, 104, points=14), fill=(229, 9, 20))
        f_b = F("heavy", 56)
        bt = f"-{disc}%"
        bw = d.textlength(bt, font=f_b)
        d.text((cx - bw / 2, cy - 34), bt, font=f_b, fill=WHITE)

    # category chip
    cat = str(p.get("category") or "Deal").strip()
    f_chip = F("bold", 34)
    ctw = d.textlength(cat, font=f_chip)
    d.rounded_rectangle([100, 352, 100 + ctw + 56, 416], radius=32,
                        fill=(26, 26, 26))
    d.text((128, 366), cat, font=f_chip, fill=YELLOW)

    # product name
    f_name = F("bold", 58)
    y = 456
    for ln in wrap(d, p.get("name", "Amazon Deal"), f_name, 700)[:3]:
        d.text((100, y), ln, font=f_name, fill=INK)
        y += 74
    y += 24

    # price block
    price = str(p.get("price", "")).strip() or "₹?"
    mrp = str(p.get("mrp", "")).strip()
    f_price = F("heavy", 128)
    d.text((100, y), price, font=f_price, fill=GREEN)
    pw = d.textlength(price, font=f_price)
    if mrp and mrp != price:
        f_mrp = F("regular", 54)
        d.text((130 + pw, y + 72), mrp, font=f_mrp, fill=GREY)
        mw = d.textlength(mrp, font=f_mrp)
        d.line([(132 + pw, y + 104), (132 + pw + mw, y + 104)],
               fill=GREY, width=5)
    y += 196

    # rating stars (vector — no glyph risk on CI's DejaVu)
    rating = str(p.get("rating", "")).strip()
    try:
        rv = float(re.sub(r"[^\d.]", "", rating) or 0)
    except ValueError:
        rv = 0.0
    if rv:
        full = int(round(rv))
        sx, sy = 124, y + 22
        for i in range(5):
            col = (255, 184, 0) if i < full else (216, 216, 216)
            d.polygon(star_poly(sx + i * 58, sy, 24, 11), fill=col)
        d.text((sx + 5 * 58 + 6, sy - 23), f"{rating} / 5",
               font=F("regular", 38), fill=(95, 95, 95))
        y += 76

    # hook line
    fix = str(p.get("fix") or p.get("hook") or "").strip()
    if fix:
        f_fix = F("regular", 38)
        for ln in wrap(d, fix, f_fix, 760)[:3]:
            d.text((100, y), ln, font=f_fix, fill=(85, 85, 85))
            y += 50
        y += 12

    # trust row: green check dot + line
    d.ellipse([100, y + 8, 126, y + 34], fill=GREEN)
    d.line([(106, y + 22), (112, y + 28), (120, y + 15)], fill=WHITE, width=4)
    d.text((142, y + 2), "Amazon India · easy returns",
           font=F("regular", 36), fill=(120, 120, 120))

    # --- CTA pill + domain ---
    d.rounded_rectangle([56, 1240, W - 56, 1384], radius=72, fill=YELLOW)
    f_cta = F("bold", 54)
    ct2 = "GRAB THE DEAL →"
    cw = d.textlength(ct2, font=f_cta)
    d.text(((W - cw) / 2, 1284), ct2, font=f_cta, fill=INK)
    f_dom = F("regular", 34)
    dt = "smartgahr.netlify.app · new deals daily"
    dw = d.textlength(dt, font=f_dom)
    d.text(((W - dw) / 2, 1416), dt, font=f_dom, fill=(160, 160, 160))
    return img


def slug(p, i):
    name = re.sub(r"[^a-z0-9]+", "_", str(p.get("name", "")).lower()).strip("_")[:40]
    # link-hash (not loop index) so CI and local renders produce identical
    # filenames — order changes as pins get deduped, hash never does.
    h = hashlib.md5(str(p.get("link", "")).encode("utf-8")).hexdigest()[:8]
    return f"pin_v2_{h}_{name}.png"


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


def write_status(res, limit):
    """Persist a run report so CI failures are diagnosable without log access."""
    from datetime import datetime, timezone

    res = dict(res)
    res["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    res["limit"] = limit
    try:
        res["pinned_total"] = len(load_pinned())
    except Exception:
        res["pinned_total"] = None
    STATUS.write_text(json.dumps(res, indent=2), encoding="utf-8")


def upload(items, limit=None, key_suffix=""):
    """Upload pins; always returns a report dict (never a bare None).

    key_suffix: dedup key modifier — "" for a product's first pin,
    "|v2" for the second design pass (see main()).
    """
    import requests
    res = {
        "token_present": False,
        "boards_found": 0,
        "uploaded": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
    }

    def fail(msg):
        res["failed"] += 1
        if len(res["errors"]) < 5:
            res["errors"].append(msg[:240])
        print(f"FAIL: {msg[:240]}")

    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if not token:
        print("PINTEREST_ACCESS_TOKEN missing — GitHub repo secret set karo.")
        res["errors"].append("PINTEREST_ACCESS_TOKEN missing in environment")
        return res
    res["token_present"] = True

    h = {"Authorization": f"Bearer {token}"}
    boards = get_boards(h)
    res["boards_found"] = len(boards)
    if not boards:
        res["errors"].append(
            "get_boards returned no boards — token invalid/expired or missing scopes"
        )
        return res

    pinned = load_pinned()
    done = 0

    for path, p in items:
        if limit is not None and done >= limit:
            print(f"daily quota reached ({limit} pins)")
            break
        key = str(p.get("link", "")) + key_suffix
        if key in pinned:
            print(f"skip (already pinned): {path.name}")
            res["skipped"] += 1
            continue
        cat = p.get("category") or ""
        board_name = BOARD_MAP.get(cat, FALLBACK_BOARD)
        board_id = boards.get(board_name) or boards.get(FALLBACK_BOARD)
        if not board_id:
            fail(f"no board found for {board_name!r}")
            continue

        title = f"{p.get('name','Amazon Deal')} — {p.get('price','')} ({p.get('discount_percent','')} off)"
        if key_suffix:
            # v2 pass runs during the BF wave — front-load the search terms
            # shoppers actually type ("BF 2026 deal") instead of a generic title.
            title = (f"BF 2026 Deal: {p.get('name','Amazon Deal')} "
                     f"{p.get('price','')} ({p.get('discount_percent','')} off)")
        title = title[:95]  # Pinterest title cap ~100
        # Never claim "under ₹999" for a ₹25,000 TV — that reads as bait and
        # kills trust on a brand-new account.
        px = price_num(p)
        budget = "Verified Amazon India deal under ₹999" if 0 < px <= 999 else "Hand-checked Amazon India deal"
        bf_lead = "Black Friday 2026 India deal. " if key_suffix else ""
        desc = (f"{bf_lead}{p.get('fix') or p.get('hook','')} "
                f"MRP {p.get('mrp','')} → {p.get('price','')} "
                f"({p.get('discount_percent','')} off, ⭐{p.get('rating','')}/5). "
                f"{budget}. More daily deals: "
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
                "link": product_page_url(p),
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
            res["uploaded"] += 1
            print(f"PINNED -> {board_name}: {title[:60]} ({pid})")
        else:
            fail(f"{path.name} — HTTP {r.status_code} {r.text[:250]}")
    print(f"uploaded {done} pin(s) this run")
    return res


def main():
    load_env()
    args = sys.argv[1:]

    daily = None
    if "--daily" in args:
        idx = args.index("--daily")
        daily = int(args[idx + 1]) if idx + 1 < len(args) and args[idx + 1].isdigit() else 2

    upload_all = "--upload-all" in args
    do_upload = "--upload" in args or upload_all or daily is not None
    key_suffix = ""  # v2 second-pass dedup key (link|v2); "" = normal first pass
    nums = [a for a in args if a.isdigit() and a != (str(daily) if daily else "")]
    n = int(nums[0]) if nums else (999 if (upload_all or daily) else 5)

    if upload_all or daily is not None:
        # High-ticket first: pin highest expected-commission deals before cheap
        # filler; skip already-pinned so we only render what's actually needed.
        OUT.mkdir(exist_ok=True)
        pinned = load_pinned()
        items = []
        prods = [p for p in load_products() if str(p.get("link", "")) not in pinned]
        if not prods:
            # Every deal already pinned once (queue dry) → keep the drip alive
            # with a second pass in the NEW v2 design. Pinterest sees a fresh
            # image + BF-tuned title, so it reads as a new pin, not a dupe.
            prods = [p for p in load_products()
                     if str(p.get("link", "")) + "|v2" not in pinned]
            key_suffix = "|v2"
            print(f"v1 queue dry -> v2 design pass: {len(prods)} deal(s)")
        prods.sort(key=commission_score, reverse=True)
        # Round-robin across categories: pure commission order sent every pin to
        # Electronics and left the other 3 boards dead. This keeps each board
        # active while still starting with the highest-payout deal.
        buckets = {}
        for p in prods:
            buckets.setdefault(p.get("category") or "Deals", []).append(p)
        # Categories ranked by their best payout, then strict round-robin so no
        # board is starved (2 pins/day, 4 boards = every board gets pins).
        cats = sorted(buckets, key=lambda c: commission_score(buckets[c][0]), reverse=True)
        mixed = []
        while any(buckets[c] for c in cats):
            for c in cats:
                if buckets[c]:
                    mixed.append(buckets[c].pop(0))
        prods = mixed
        # CI only needs a few cards per run — rendering all 47 wasted ~1 min
        if not upload_all and daily:
            prods = prods[: daily + 4]
        for i, p in enumerate(prods, 1):
            path = OUT / slug(p, i)
            if not path.exists():
                path.parent.mkdir(exist_ok=True)
                card(p).save(path, "PNG")
            items.append((path, p))
        print(f"{len(items)} unpinned cards ready in pins/ (high-ticket first)")
    else:
        items = generate(n)

    if do_upload:
        print("\n--- Uploading to Pinterest ---")
        res = upload(items, limit=daily, key_suffix=key_suffix)
        write_status(res, daily)

        # Exit non-zero so a broken token shows up as a red CI run instead of
        # a green no-op (that silently stalled the drip for days).
        if not res.get("token_present"):
            return 1
        if res.get("boards_found", 0) == 0:
            return 1
        if res.get("uploaded", 0) == 0 and res.get("failed", 0) > 0:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
