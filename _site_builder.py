#!/usr/bin/env python3
"""SmartGahr site builder.

Reads product.json and regenerates:
  netlify-redirector/index.html       - landing page (hero + top deals)
  netlify-redirector/deals/index.html - all deals grouped by category
  netlify-redirector/sitemap.xml      - sitemap

Run:  python _site_builder.py
"""
import json
import html
from pathlib import Path
from urllib.parse import quote
from datetime import date

ROOT = Path(__file__).resolve().parent
PRODUCTS_FILE = ROOT / "product.json"
SITE_DIR = ROOT / "netlify-redirector"
DEALS_DIR = SITE_DIR / "deals"
BASE_URL = "https://smartgahr.netlify.app"
CHANNEL_URL = "https://t.me/smartgahr"
BUILT_DATE = date.today().strftime("%Y-%m-%d")

CATEGORY_ICONS = {
    "Electronics": "\U0001F3A7",
    "Home & Kitchen": "\U0001F373",
    "Home Improvement": "\U0001F528",
    "Beauty & Personal Care": "\U0001F484",
    "Fashion": "\U0001F457",
    "Books": "\U0001F4DA",
}

def esc(s):
    return html.escape(str(s or ""))

def discount_num(p):
    try:
        return int(str(p.get("discount_percent") or "0").replace("%", "").strip() or 0)
    except ValueError:
        return 0

def load_products():
    data = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    seen = set()
    out = []
    for p in data.get("products", []):
        link = (p.get("link") or "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        out.append(p)
    return out

def deal_href(link):
    return "go?url=" + quote(link, safe="")

def deal_card(p, rel):
    cat = esc(p.get("category") or "Deals")
    icon = CATEGORY_ICONS.get(p.get("category") or "", "\U0001F6D2")
    price = esc(p.get("price") or "")
    mrp = esc(p.get("mrp") or "")
    rating = p.get("rating")
    disc = discount_num(p)
    badge = f'<span class="badge">{disc}% OFF</span>' if disc else ""
    rating_html = f'<span class="deal-rating">⭐ {esc(rating)}/5</span>' if rating else ""
    href = rel + deal_href(p.get("link") or "")
    return f"""      <article class="deal-card">
        {badge}
        <div class="deal-body">
          <div class="deal-cat">{icon} {cat}</div>
          <h3 class="deal-title">{esc(p.get('name'))}</h3>
          <div class="deal-price-row">
            <span class="deal-price">{price}</span>
            {f'<span class="deal-mrp">{mrp}</span>' if mrp else ''}
            {rating_html}
          </div>
          <a class="btn btn-deal deal-cta" href="{href}" rel="nofollow sponsored noopener" target="_blank">View Deal →</a>
        </div>
      </article>"""

def head(title, desc, canonical, rel=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{BASE_URL}/og-image.jpg">
  <link rel="stylesheet" href="{rel}style.css">
</head>"""

HEADER = """<header class="site-header">
  <div class="container">
    <a href="{home}" class="logo">Smart<span>Gahr</span></a>
    <nav class="nav">
      <a href="{home}">Home</a>
      <a href="{deals}">Deals</a>
      <a href="{about}">About</a>
      <a href="{contact}">Contact</a>
    </nav>
  </div>
</header>"""

FOOTER = """<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div>© 2026 SmartGahr. All deals verified.</div>
      <div class="footer-links">
        <a href="{home}">Home</a>
        <a href="{deals}">Deals</a>
        <a href="{about}">About</a>
        <a href="{contact}">Contact</a>
        <a href="privacy.html">Privacy</a>
        <a href="disclaimer.html">Disclaimer</a>
      </div>
    </div>
    <div class="footer-note">As an Amazon Associate we earn from qualifying purchases. Prices change fast — always confirm on Amazon.</div>
  </div>
</footer>"""

def build_header(rel):
    return HEADER.format(
        home=rel + "index.html",
        deals=rel + "deals/index.html",
        about=rel + "about.html",
        contact=rel + "contact.html",
    )

def build_footer(rel):
    return FOOTER.format(
        home=rel + "index.html",
        deals=rel + "deals/index.html",
        about=rel + "about.html",
        contact=rel + "contact.html",
    )

def build_index(products):
    top = sorted(products, key=discount_num, reverse=True)[:8]
    cats = []
    for p in products:
        c = p.get("category") or "Deals"
        if c not in cats:
            cats.append(c)
    chips = "".join(
        f'<a class="chip" href="deals/index.html#{quote(c.lower().replace(" ", "-"))}">{CATEGORY_ICONS.get(c, "\U0001F6D2")} {esc(c)}</a>'
        for c in cats
    )
    cards = "\n".join(deal_card(p, "") for p in top)
    doc = f"""{head('SmartGahr — Verified Amazon Deals Under ₹999', 'Daily verified Amazon India deals under ₹999 with 40%+ off. Join 1,000+ smart shoppers saving money daily.', BASE_URL + '/')}
<body>
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header('')}
<main>
  <section class="hero">
    <div class="container">
      <h1>🔥 Today's Best Amazon Deals Under ₹999</h1>
      <p>Every deal verified — 40%+ off, 4★+ ratings, real prices only. New loot deals daily.</p>
      <div class="cta-row">
        <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Join Telegram Channel</a>
        <a class="btn btn-outline" href="deals/index.html">Browse All Deals</a>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head">
        <h2>🏷️ Today's Top Deals</h2>
        <a href="deals/index.html">View all →</a>
      </div>
      <div class="chips">{chips}</div>
      <div class="deal-grid">
{cards}
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="channel-band">
        <h2>📲 Get Deals Instantly on Telegram</h2>
        <p>Website pe aana bhool jayoge — deals seedha Telegram par roz aate hain.</p>
        <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Join @smartgahr Free</a>
      </div>
    </div>
  </section>
</main>
{build_footer('')}
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(doc, encoding="utf-8")

def build_deals_page(products):
    by_cat = {}
    for p in products:
        by_cat.setdefault(p.get("category") or "Deals", []).append(p)
    sections = []
    for cat in sorted(by_cat.keys()):
        anchor = quote(cat.lower().replace(" ", "-"))
        cards = "\n".join(deal_card(p, "../") for p in by_cat[cat])
        sections.append(f"""  <section class="section" id="{anchor}">
    <div class="container">
      <div class="section-head"><h2>{CATEGORY_ICONS.get(cat, chr(128722))} {esc(cat)}</h2></div>
      <div class="deal-grid">
{cards}
      </div>
    </div>
  </section>""")
    body = "\n\n".join(sections)
    doc = f"""{head('All Deals — SmartGahr', f'{len(products)} verified Amazon deals under ₹999 with 40%+ discounts.', BASE_URL + '/deals/', rel='../')}
<body>
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header('../')}
<main>
  <section class="hero">
    <div class="container">
      <h1>🛒 All Verified Deals</h1>
      <p>{len(products)} live deals — all under ₹999, all 40%+ off. Updated daily.</p>
    </div>
  </section>
{body}
  <section class="section">
    <div class="container">
      <div class="channel-band">
        <h2>📲 Roj naye deals Telegram par</h2>
        <p>Sabse tez deals paane ke liye channel join karo.</p>
        <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Join @smartgahr Free</a>
      </div>
    </div>
  </section>
</main>
{build_footer('../')}
</body>
</html>
"""
    DEALS_DIR.mkdir(exist_ok=True)
    (DEALS_DIR / "index.html").write_text(doc, encoding="utf-8")

def build_sitemap():
    urls = [
        ("/", "1.0"),
        ("/deals/", "0.9"),
        ("/about.html", "0.3"),
        ("/contact.html", "0.3"),
        ("/privacy.html", "0.2"),
        ("/disclaimer.html", "0.2"),
    ]
    entries = "\n".join(
        f"  <url>\n    <loc>{BASE_URL}{u}</loc>\n    <lastmod>{BUILT_DATE}</lastmod>\n    <priority>{pr}</priority>\n  </url>"
        for u, pr in urls
    )
    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
"""
    (SITE_DIR / "sitemap.xml").write_text(doc, encoding="utf-8")

def main():
    products = load_products()
    if not products:
        print("No products in product.json — skipping site build")
        return
    build_index(products)
    build_deals_page(products)
    build_sitemap()
    print(f"Site built: {len(products)} deals -> index.html, deals/index.html, sitemap.xml")

if __name__ == "__main__":
    main()
