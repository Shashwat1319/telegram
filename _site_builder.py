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
import re
from pathlib import Path
from urllib.parse import quote
from datetime import date

ROOT = Path(__file__).resolve().parent
PRODUCTS_FILE = ROOT / "product.json"
IMAGES_FILE = ROOT / "product_images.json"
SITE_DIR = ROOT / "netlify-redirector"
DEALS_DIR = SITE_DIR / "deals"
BASE_URL = "https://smartgahr.netlify.app"
CHANNEL_URL = "https://t.me/smartgahr"
BUILT_DATE = date.today().strftime("%Y-%m-%d")
BUILT_DATE_HUMAN = f"{date.today().day} {date.today().strftime('%b %Y')}"

# Categories with at least this many deals get their own landing page.
# (Fewer than this -> page would be thin, so those deals stay on /deals/ only.)
MIN_CATEGORY_DEALS = 3

CATEGORY_ICONS = {
    "Electronics": "\U0001F3A7",
    "Home & Kitchen": "\U0001F373",
    "Home Improvement": "\U0001F528",
    "Beauty & Personal Care": "\U0001F484",
    "Fashion": "\U0001F457",
    "Books": "\U0001F4DA",
}

# Landing-page copy for categories big enough to deserve their own URL.
# Each gets a 200+ word unique intro (Google rewards it over a bare list) plus
# FAQ blocks that also power FAQPage structured data.
CATEGORY_PAGES = {
    "Electronics": {
        "slug": "electronics",
        "h1": "Amazon Electronics Deals — Verified Prices, Updated Daily",
        "title": "Amazon Electronics Deals Under ₹999 — SmartGahr",
        "desc": "Verified Amazon India electronics deals: earbuds, smartwatches, speakers and TVs at 40%+ off with 4★+ ratings. Prices checked daily.",
        "intro": [
            "Electronics pe discount sabse zyada dikhta hai — aur fake MRP games bhi sabse zyada yahin hoti hain. "
            "Is page pe sirf woh deals hain jinka price humne khud Amazon pe check kiya hai: 40%+ off, 4★ se upar "
            "rating, aur ek genuine seller. Koi \"90% off\" wala clickbait nahi.",
            "Yahan earbuds, TWS, smartwatches, speakers aur TVs sab aate hain — sabse sasta ₹149 se lekar premium "
            "₹29,999 tak. Dhyan rakho: electronics deals sabse tezi se khatam hote hain, kyunki ek hi unit par "
            "discount chalta hai. Deal pasand aaye toh price dobara check karke turant order karo.",
        ],
        "faq": [
            ("Are these electronics prices real?", "Haan. Har deal ka price aur MRP Amazon ke live product page se aata hai, aur hum 40% se kam discount wale deals publish hi nahi karte. Phir bhi Amazon ke prices har kuch ghanton mein badalte hain, isliye final price Amazon pe hi confirm karo."),
            ("Why do some deals disappear after a day?", "Kyunki deal stock khatam ho jata hai. Jab seller ka discounted stock bik jata hai, price wapas badh jata hai — hum us deal ko list se hata dete hain taaki tu purane price pe click karke disappoint na ho."),
            ("Do I pay more by buying through SmartGahr?", "Nahi. Price bilkul wahi rehta hai jo Amazon pe dikhta hai. Hum Amazon Associates ka affiliate commission kamate hain, tere se extra ek rupaya nahi lete."),
        ],
    },
    "Home & Kitchen": {
        "slug": "home-kitchen",
        "h1": "Home & Kitchen Deals — Amazon India Offers Under ₹999",
        "title": "Amazon Home & Kitchen Deals Under ₹999 — SmartGahr",
        "desc": "Amazon India home and kitchen deals: cookware, storage, cleaning and small appliances at 40%+ off with 4★+ ratings. Verified daily.",
        "intro": [
            "Ghar ka saman woh kharid hai jo har mahine padti hai — aur yahin sabse zyada paisa waste hota hai, "
            "kyunki MRP aur actual selling price mein zameen-aasman ka farak hota hai. Hum roz woh kitchen aur home "
            "products dhoondte hain jahan discount sach mein hai: cookware, storage boxes, cleaning tools, "
            "mixer-grinder jaise chhote appliances.",
            "Yahan sab kuch ₹215 se ₹7,999 ke beech hai. Kitchen ke liye ek simple rule jo hum khud follow karte "
            "hain: non-stick aur cooker jaise items mein brand se zyada warranty dekho, aur storage/organiser "
            "mein size dimensions check karo — discount ke chakkar mein galat size sabse common galti hai.",
        ],
        "faq": [
            ("Are these kitchen products good quality?", "Hum sirf 4★ aur usse upar rating wale products list karte hain, aur ratings kam se kam 100+ honi chahiye. Lekin har ghar ki zaroorat alag hoti hai — order se pehle size, capacity aur warranty zaroor check kar lena."),
            ("Are the discounts on MRP or real price?", "Hum MRP ka discount dikhate hain lekin sirf tab jab product ka current selling price genuinely neeche ho. Sirf MRP inflated karke dikhaya gaya \"discount\" hum list nahi karte."),
            ("How often is this page updated?", "Roz. Prices change hote rehte hain aur khatam ho chuke deals hata diye jaate hain. Page ke top pe last updated date dikhti hai."),
        ],
    },
    "Home Improvement": {
        "slug": "home-improvement",
        "h1": "Home Improvement Deals — Tools & Hardware Offers on Amazon",
        "title": "Amazon Home Improvement Deals — SmartGahr",
        "desc": "Verified Amazon India home improvement deals: hand tools, drill bits, fittings, LED lights and hardware at 40%+ off with 4★+ ratings.",
        "intro": [
            "Chhote repair — loose hinge, kharab switch, naya curtain rod — ke liye har baar mistri bulana mehnga "
            "padta hai. Is page pe woh tools aur hardware hain jinse kaam khud ho jata hai: screwdriver sets, "
            "drill bits, wall fittings, LED lights, taps aur bathroom accessories.",
            "Range ₹199 se ₹2,499 tak hai, matlab ek basic toolkit ka kharcha ek mistri ki ek visit se kam. "
            "Tools kharidte waqt material dekhna zaroori hai — carbon steel thoda sasta hota hai par chrome "
            "vanadium zyada tikta hai. Hum dono tarah ke options list karte hain taaki tu apni zaroorat ke hisaab "
            "se chun sake.",
        ],
        "faq": [
            ("Are these tools suitable for home use?", "Haan, ye zyadatar ghar ke basic repair ke liye hain — furniture, switches, bathroom fittings. Heavy professional use ke liye industrial grade chahiye hoga, jo is list mein nahi hai."),
            ("Do the tools come with warranty?", "Kuch brands par 1-6 mahine ki warranty hoti hai, kuch par nahi. Product page pe warranty section check kar lena — hum wahi deals list karte hain jahan seller aur return policy clear ho."),
            ("Can I return a tool if the size doesn't fit?", "Amazon ke standard return window ke andar haan, agar product returnable mark hai. Fittings aur drill bits mein size pehle check karna best hai, kyunki return mein time jata hai."),
        ],
    },
}

CATEGORY_LINK_TEXT = "Browse all {n} {cat} deals →"


def category_meta(cat):
    """Return landing-page meta for a category, or None if it shouldn't get a page."""
    meta = CATEGORY_PAGES.get(cat)
    if meta:
        return meta
    slug = (
        cat.lower()
        .replace("&", "and")
        .replace(",", "")
        .replace("  ", " ")
        .replace(" ", "-")
    )
    return {
        "slug": slug,
        "h1": f"{cat} Deals on Amazon India",
        "title": f"{cat} Deals on Amazon India — Verified Offers | SmartGahr",
        "desc": f"Verified Amazon India {cat.lower()} deals at 40%+ off with 4★+ ratings. Prices checked daily.",
        "intro": [
            f"Hand-picked {cat.lower()} deals from Amazon India — sirf woh offers jinke price humne khud verify kiye: "
            "40%+ off aur 4★+ rating. Prices roz check hote hain aur expired deals hata diye jaate hain.",
        ],
        "faq": [
            ("How are these deals verified?", "Har deal ka price, rating aur discount Amazon ke live product page se liya jata hai. 40% se kam discount wale products list nahi hote."),
            ("Do I pay extra for buying through these links?", "Nahi — price wahi rehta hai. Hum Amazon Associates affiliate commission kamate hain, buyer se extra charge nahi."),
        ],
    }


def categories_with_pages(products):
    """Categories that have enough deals for a standalone landing page."""
    counts = {}
    for p in products:
        counts[p.get("category") or "Deals"] = counts.get(p.get("category") or "Deals", 0) + 1
    return {c for c, n in counts.items() if n >= MIN_CATEGORY_DEALS and c != "Deals"}


def category_path(cat):
    return f"deals/{category_meta(cat)['slug']}/"

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


def load_images():
    """link -> site-relative image path (product_images.json is written by fetch_images.py)."""
    if not IMAGES_FILE.exists():
        return {}
    try:
        data = json.loads(IMAGES_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    out = {}
    for link, entry in (data or {}).items():
        file_rel = entry.get("file") if isinstance(entry, dict) else entry
        if file_rel and (SITE_DIR / file_rel).exists():
            out[link] = file_rel
    return out

def deal_href(link):
    return "go?url=" + quote(link, safe="")


def slugify(text):
    out = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return out or "deal"


_IMAGES = None


def product_image(link):
    """Cached lookup of the local product image path for an affiliate link."""
    global _IMAGES
    if _IMAGES is None:
        _IMAGES = load_images()
    return _IMAGES.get(link)


def jsonld(data):
    """Serialize structured data safely for inline <script>."""
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    return "<script type=\"application/ld+json\">\n" + raw.replace("</", "<\\/") + "\n</script>"


def faq_block(faqs, title="Common questions"):
    items = "\n".join(
        f"""      <details class="faq-item">
        <summary>{esc(q)}</summary>
        <p>{esc(a)}</p>
      </details>"""
        for q, a in faqs
    )
    return f"""  <section class="section">
    <div class="container">
      <div class="section-head"><h2>❓ {esc(title)}</h2></div>
      <div class="faq">
{items}
      </div>
    </div>
  </section>"""


def faq_schema(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faqs
        ],
    }


def item_list_schema(products, page_url, slug_prefix):
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Verified Amazon deals",
        "numberOfItems": len(products),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": p.get("name") or "Deal",
                "url": f"{page_url}#{slug_prefix}-{slugify(p.get('name'))}",
            }
            for i, p in enumerate(products, 1)
        ],
    }


def deal_card(p, rel, pid=""):
    cat = esc(p.get("category") or "Deals")
    icon = CATEGORY_ICONS.get(p.get("category") or "", "\U0001F6D2")
    price = esc(p.get("price") or "")
    mrp = esc(p.get("mrp") or "")
    rating = p.get("rating")
    disc = discount_num(p)
    badge = f'<span class="badge">{disc}% OFF</span>' if disc else ""
    rating_html = f'<span class="deal-rating">⭐ {esc(rating)}/5</span>' if rating else ""
    href = rel + deal_href(p.get("link") or "")
    id_attr = f' id="{esc(pid)}"' if pid else ""
    name = esc(p.get("name"))
    img_file = product_image((p.get("link") or "").strip())
    if img_file:
        media = (
            f'<a class="deal-media" href="{href}" rel="nofollow sponsored noopener" '
            f'target="_blank" tabindex="-1" aria-hidden="true">'
            f'<img src="{rel}{img_file}" alt="{name} — Amazon India deal" '
            f'width="300" height="300" loading="lazy" decoding="async"></a>'
        )
    else:
        media = f'<div class="deal-media ph" aria-hidden="true"><span>{icon}</span></div>'
    return f"""      <article class="deal-card"{id_attr}>
        {media}
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

def head(title, desc, canonical, rel="", head_extra=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-RJF4R9N204"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-RJF4R9N204');
  </script>
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{BASE_URL}/og-image.jpg">
  <meta property="og:site_name" content="SmartGahr">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{BASE_URL}/og-image.jpg">
  <meta name="google-site-verification" content="kDpUhMVkIw8yo4plaH4RPhK0HuJbo_boNpSStxonc34" />
  <meta name="p:domain_verify" content="cf62f1ed7feba30bde14957942317589" />
  <link rel="stylesheet" href="{rel}style.css">
  {head_extra}
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
        <a href="{kitchen}">Kitchen Finds</a>
        <a href="{about}">About</a>
        <a href="{contact}">Contact</a>
        <a href="{privacy}">Privacy</a>
        <a href="{disclaimer}">Disclaimer</a>
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
        kitchen=rel + "kitchenfinds/index.html",
        about=rel + "about.html",
        contact=rel + "contact.html",
        privacy=rel + "privacy.html",
        disclaimer=rel + "disclaimer.html",
    )

JSONLD_HOME = """<script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "SmartGahr",
    "url": "https://smartgahr.netlify.app/",
    "description": "Daily verified Amazon India deals under \u20b9999 with 40%+ off.",
    "publisher": {
      "@type": "Organization",
      "name": "SmartGahr",
      "url": "https://smartgahr.netlify.app/",
      "sameAs": ["https://t.me/smartgahr"]
    }
  }
  </script>"""


HOME_FAQ = [
    (
        "Yeh Amazon deals sach mein verified hain?",
        "Haan. Har deal ka price, MRP, rating aur discount Amazon ke live product page se aata hai. Hum sirf 40% se "
        "zyada discount aur 4★ se upar rating wale products list karte hain — isliye list chhoti lagti hai, par "
        "jhoothe \"90% off\" offers nahi milenge.",
    ),
    (
        "Deal link pe click karne se price badh jata hai?",
        "Nahi. SmartGahr link se Amazon pe jaane par price wahi rehta hai jo normally dikhta hai. Hum Amazon "
        "Associates affiliate commission kamate hain, buyer se ek rupaya extra nahi lete.",
    ),
    (
        "Naye deals kitni jaldi add hote hain?",
        "Site roz rebuild hoti hai — expired deals nikal jaate hain aur naye price drops add hote hain. Sabse tez "
        "update Telegram channel par milta hai, kyunki wahan deal publish hote hi sabko chala jata hai.",
    ),
    (
        "Kya Telegram channel join karna free hai?",
        "Bilkul free. Channel par roz verified deals jaate hain, koi paid subscription nahi hai.",
    ),
]


def chip_html(cat, page_cats):
    icon = CATEGORY_ICONS.get(cat, "\U0001F6D2")
    href = category_path(cat) if cat in page_cats else "deals/index.html#" + slugify(cat)
    return f'<a class="chip" href="{href}">{icon} {esc(cat)}</a>'


def build_index(products):
    top = sorted(products, key=discount_num, reverse=True)[:8]
    page_cats = categories_with_pages(products)
    cats = []
    for p in products:
        c = p.get("category") or "Deals"
        if c not in cats:
            cats.append(c)
    chips = "".join(chip_html(c, page_cats) for c in cats)
    cards = "\n".join(
        deal_card(p, "", pid=f"home-{slugify(p.get('name'))}") for p in top
    )
    schema = "\n  ".join(
        [
            JSONLD_HOME,
            jsonld(item_list_schema(top, BASE_URL + "/", "home")),
            jsonld(faq_schema(HOME_FAQ)),
        ]
    )
    doc = f"""{head('SmartGahr — Verified Amazon Deals Under ₹999', 'Daily verified Amazon India deals under ₹999 with 40%+ off and 4★ ratings. Fresh loot offers every day on gadgets, home and kitchen essentials.', BASE_URL + '/', head_extra=schema)}
<body>
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header('')}
<main>
  <section class="hero">
    <div class="container">
      <h1>🔥 Today's Best Amazon Deals Under ₹999</h1>
      <p>Every deal verified — 40%+ off, 4★+ ratings, real prices only. New loot deals daily.</p>
      <p class="updated">Last updated: {BUILT_DATE_HUMAN} · {len(products)} live deals</p>
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

{faq_block(HOME_FAQ, "Amazon deals ke baare mein sawaal")}
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
    page_cats = categories_with_pages(products)
    sections = []
    for cat in sorted(by_cat.keys()):
        slug = category_meta(cat)["slug"]
        cards = "\n".join(
            deal_card(p, "../", pid=f"{slug}-{slugify(p.get('name'))}") for p in by_cat[cat]
        )
        heading = f'{CATEGORY_ICONS.get(cat, chr(128722))} {esc(cat)}'
        if cat in page_cats:
            heading = f'<a href="{slug}/">{heading}</a>'
        sections.append(f"""  <section class="section" id="{slugify(cat)}">
    <div class="container">
      <div class="section-head"><h2>{heading}</h2></div>
      <div class="deal-grid">
{cards}
      </div>
    </div>
  </section>""")
    body = "\n\n".join(sections)
    schema = jsonld(item_list_schema(products, BASE_URL + "/deals/", "deals"))
    doc = f"""{head('All Amazon Deals Under ₹999 — Verified Daily | SmartGahr', f'All {len(products)} verified Amazon India deals under ₹999 with 40%+ off and 4★+ ratings, updated daily. Browse live deals by category and grab the best price drops.', BASE_URL + '/deals/', rel='../', head_extra=schema)}
<body>
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header('../')}
<main>
  <section class="hero">
    <div class="container">
      <h1>🛒 All Verified Deals</h1>
      <p>{len(products)} live deals — all under ₹999, all 40%+ off. Block ke heading pe click karke sirf woh category dekho jo chahiye.</p>
      <p class="updated">Last updated: {BUILT_DATE_HUMAN}</p>
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

def price_num(p):
    digits = re.sub(r"[^0-9]", "", str(p.get("price") or ""))
    return int(digits) if digits else 0


def build_category_pages(products):
    """One landing page per big category: unique copy + FAQ + ItemList schema."""
    by_cat = {}
    for p in products:
        by_cat.setdefault(p.get("category") or "Deals", []).append(p)
    page_cats = categories_with_pages(products)
    rel = "../../"
    built = []

    for cat in sorted(page_cats):
        items = sorted(by_cat[cat], key=discount_num, reverse=True)
        if not items:
            continue
        meta = category_meta(cat)
        slug = meta["slug"]
        page_url = f"{BASE_URL}/deals/{slug}/"
        cards = "\n".join(
            deal_card(p, rel, pid=f"{slug}-{slugify(p.get('name'))}") for p in items
        )
        prices = [n for n in (price_num(p) for p in items) if n]
        price_line = (
            f"₹{min(prices)} se ₹{max(prices)} tak" if prices else "verified prices"
        )
        others = " ".join(
            f'<a class="chip" href="../{category_meta(c)["slug"]}/">'
            f'{CATEGORY_ICONS.get(c, chr(128722))} {esc(c)}</a>'
            for c in sorted(page_cats)
            if c != cat
        )
        breadcrumb = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": "All Deals", "item": BASE_URL + "/deals/"},
                {"@type": "ListItem", "position": 3, "name": cat, "item": page_url},
            ],
        }
        schema = "\n  ".join(
            [
                jsonld(breadcrumb),
                jsonld(item_list_schema(items, page_url, slug)),
                jsonld(faq_schema(meta["faq"])),
            ]
        )
        intro = "\n".join(f"      <p>{esc(t)}</p>" for t in meta["intro"])
        doc = f"""{head(meta["title"], meta["desc"], page_url, rel=rel, head_extra=schema)}
<body>
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header(rel)}
<main>
  <section class="hero">
    <div class="container">
      <h1>{esc(meta["h1"])}</h1>
{intro}
      <p class="updated">{len(items)} verified deals · {price_line} · Updated {BUILT_DATE_HUMAN}</p>
      <div class="cta-row">
        <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Get Deals on Telegram</a>
        <a class="btn btn-outline" href="../">All deals →</a>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head">
        <h2>{CATEGORY_ICONS.get(cat, chr(128722))} {esc(cat)} deals</h2>
        <a href="../">View everything →</a>
      </div>
      <div class="deal-grid">
{cards}
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head"><h2>🗂️ Other categories</h2></div>
      <div class="chips">{others}</div>
    </div>
  </section>

{faq_block(meta["faq"], cat + " deals ke baare mein sawaal")}
</main>
{build_footer(rel)}
</body>
</html>
"""
        out_dir = DEALS_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(doc, encoding="utf-8")
        built.append(f"/deals/{slug}/")

    return built


def build_image_sitemap(products):
    """List local product images so Google Images can find them."""
    images = load_images()
    entries = []
    for p in products:
        file_rel = images.get((p.get("link") or "").strip())
        if not file_rel:
            continue
        name = esc(p.get("name") or "Amazon deal")
        entries.append(
            f"    <image:image>\n"
            f"      <image:loc>{BASE_URL}/{file_rel}</image:loc>\n"
            f"      <image:title>{name}</image:title>\n"
            f"      <image:caption>{name} — verified Amazon India deal</image:caption>\n"
            f"    </image:image>"
        )
    if not entries:
        return 0
    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>{BASE_URL}/deals/</loc>
    <lastmod>{BUILT_DATE}</lastmod>
{chr(10).join(entries)}
  </url>
</urlset>
"""
    (SITE_DIR / "sitemap-images.xml").write_text(doc, encoding="utf-8")
    return len(entries)


def build_sitemap(extra_urls=()):
    urls = [
        ("/", "1.0"),
        ("/deals/", "0.9"),
        *[(u, "0.8") for u in extra_urls],
        ("/kitchenfinds/", "0.7"),
        ("/about.html", "0.3"),
        ("/contact.html", "0.3"),
        ("/privacy.html", "0.2"),
        ("/disclaimer.html", "0.2"),
        ("/kitchenfinds/privacy.html", "0.2"),
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
    cats = build_category_pages(products)
    build_sitemap(cats)
    n_images = build_image_sitemap(products)
    print(
        f"Site built: {len(products)} deals -> index.html, deals/index.html, "
        f"{len(cats)} category page(s), sitemap.xml, sitemap-images.xml ({n_images} images)"
    )

if __name__ == "__main__":
    main()
