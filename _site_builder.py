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
import shutil
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
WHATSAPP_CHANNEL_URL = "https://whatsapp.com/channel/0029VbA209B17EmmO7QhYe0w"
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
        "title": "Amazon Electronics Deals — Verified Prices | SmartGahr",
        "desc": "Verified Amazon India electronics deals: earbuds, smartwatches, speakers and TVs with 4★+ ratings and real price drops. Prices checked daily.",
        "intro": [
            "Electronics pe discount sabse zyada dikhta hai — aur fake MRP games bhi sabse zyada yahin hoti hain. "
            "Is page pe sirf woh deals hain jinka price humne khud Amazon pe check kiya hai: real discount, 4★ se upar "
            "rating, aur ek genuine seller. ₹999 se kam wale har deal pe 40%+ off. Koi \"90% off\" wala clickbait nahi.",
            "Yahan earbuds, TWS, smartwatches, speakers aur TVs sab aate hain — sabse sasta ₹149 se lekar premium "
            "₹29,999 tak. Dhyan rakho: electronics deals sabse tezi se khatam hote hain, kyunki ek hi unit par "
            "discount chalta hai. Deal pasand aaye toh price dobara check karke turant order karo.",
        ],
        "faq": [
            ("Are these electronics prices real?", "Haan. Har deal ka price aur MRP Amazon ke live product page se aata hai. Budget picks (₹999 se kam) mein hum 40% se kam discount wale deals publish nahi karte; premium products sirf tab list hote hain jab unka price genuinely neeche ho. Phir bhi Amazon ke prices har kuch ghanton mein badalte hain, isliye final price Amazon pe hi confirm karo."),
            ("Why do some deals disappear after a day?", "Kyunki deal stock khatam ho jata hai. Jab seller ka discounted stock bik jata hai, price wapas badh jata hai — hum us deal ko list se hata dete hain taaki tu purane price pe click karke disappoint na ho."),
            ("Do I pay more by buying through SmartGahr?", "Nahi. Price bilkul wahi rehta hai jo Amazon pe dikhta hai. Hum Amazon Associates ka affiliate commission kamate hain, tere se extra ek rupaya nahi lete."),
        ],
    },
    "Home & Kitchen": {
        "slug": "home-kitchen",
        "h1": "Home & Kitchen Deals — Amazon India Offers",
        "title": "Amazon Home & Kitchen Deals — Verified | SmartGahr",
        "desc": "Amazon India home and kitchen deals: cookware, storage, cleaning and small appliances with 4★+ ratings and real price drops. Verified daily.",
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
        "desc": "Verified Amazon India home improvement deals: hand tools, drill bits, fittings, LED lights and hardware with 4★+ ratings and real price drops.",
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

# Client-side price filter for the deals page (no duplicate URLs, no reload).
FILTER_JS = """<script>
(function () {
  var btns = Array.prototype.slice.call(document.querySelectorAll("[data-price-filter]"));
  var cards = Array.prototype.slice.call(document.querySelectorAll(".deal-card"));
  var note = document.querySelector(".filter-note");
  if (!btns.length || !cards.length) return;

  function apply(limit) {
    var shown = 0;
    cards.forEach(function (card) {
      var px = parseFloat(card.getAttribute("data-price") || "0");
      var hide = limit && px > limit;
      card.classList.toggle("is-hidden", !!hide);
      if (!hide) shown++;
    });
    Array.prototype.forEach.call(document.querySelectorAll(".section[id]"), function (sec) {
      var any = sec.querySelector(".deal-card:not(.is-hidden)");
      sec.classList.toggle("is-hidden", !any);
    });
    if (note) {
      note.textContent = limit
        ? shown + " deals ₹" + limit + " se kam dikha rahe hain."
        : "";
    }
  }

  btns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      btns.forEach(function (b) { b.classList.toggle("is-active", b === btn); });
      var raw = btn.getAttribute("data-price-filter");
      apply(raw ? parseFloat(raw) : 0);
    });
  });
})();
</script>"""


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
        "title": f"{cat} Deals on Amazon India | SmartGahr",
        "desc": f"Verified Amazon India {cat.lower()} deals: real price drops, 4★+ ratings and honest discounts only. New offers added daily.",
        "intro": [
            f"Hand-picked {cat.lower()} deals from Amazon India — sirf woh offers jinke price humne khud verify kiye: "
            "real discount aur 4★+ rating. Prices roz check hote hain aur expired deals hata diye jaate hain.",
        ],
        "faq": [
            ("How are these deals verified?", "Har deal ka price, rating aur discount Amazon ke live product page se liya jata hai. ₹999 se kam wale budget picks 40%+ off hote hain; premium products sirf genuine price drops par list hote hain."),
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


# affiliate link -> site-relative "deals/<category>/<product-slug>/" path.
# Filled by assign_product_paths() before any page is rendered; deal_card links
# its title here so every card feeds internal links to the product pages.
PRODUCT_PATHS = {}


def assign_product_paths(products):
    used = set()
    for p in products:
        link = (p.get("link") or "").strip()
        if not link:
            continue
        cat = p.get("category") or "Deals"
        base = f"deals/{category_meta(cat)['slug']}/{slugify(p.get('name'))}/"
        path, n = base, 2
        while path in used:
            path = base[:-1] + f"-{n}/"
            n += 1
        used.add(path)
        PRODUCT_PATHS[link] = path


_IMAGES = None


def product_image(link):
    """Cached lookup of the local product image path for an affiliate link."""
    global _IMAGES
    if _IMAGES is None:
        _IMAGES = load_images()
    return _IMAGES.get(link)


def schema_brand(name):
    """Extract brand for Product schema (GSC 'no global identifier' fix).

    Known multi-word brands matched first, else first word of the title.
    """
    multi = (
        "TIED RIBBONS", "Pigeon by Stovekraft", "Amazon Basics", "AmazonBasics",
        "Simple Kind", "Shadow Gecko", "GO24 Pexpo", "Presto!", "PCI Experto",
        "RO Metal", "Colorbot", "Btag", "Storio", "Lifelong", "Butterfly",
        "Cello", "Mortein", "Zebronics", "TP-Link", "realme", "GOBOULT",
        "INEFABLE", "Softspun", "Litverse", "Verofive", "Vervenix", "Goldmedal",
        "Wipro", "Orient Electric", "Crompton", "Havells", "Milton", "Prestige",
        "AJ DEZINES", "Majestic Man", "Gesto Edison",
        "Hawkins", "Pigeon", "Portronics", "Ambrane", "Xiaomi", "Redmi",
        "Philips", "OnePlus", "Samsung", "Apple", "JBL", "boAt", "Noise",
        "pTron", "Amazon",
    )
    upper = name.upper()
    for b in multi:
        if upper.startswith(b.upper()):
            return b
    return name.split()[0] if name.split() else "Generic"


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
    px = int(price_num(p) or 0)
    name = esc(p.get("name"))
    detail_path = PRODUCT_PATHS.get((p.get("link") or "").strip())
    title_html = f'<a href="{rel}{detail_path}">{name}</a>' if detail_path else name
    # image follows the title: detail page when we have one, else straight to Amazon
    media_href = f"{rel}{detail_path}" if detail_path else href
    img_file = product_image((p.get("link") or "").strip())
    if img_file:
        media_target = (
            ""
            if detail_path
            else ' rel="nofollow sponsored noopener" target="_blank"'
        )
        media = (
            f'<a class="deal-media" href="{media_href}"{media_target} '
            f'tabindex="-1" aria-hidden="true">'
            f'<img src="{rel}{img_file}" alt="{name} — Amazon India deal" '
            f'width="300" height="300" loading="lazy" decoding="async"></a>'
        )
    else:
        media = f'<div class="deal-media ph" aria-hidden="true"><span>{icon}</span></div>'
    return f"""      <article class="deal-card"{id_attr} data-price="{px}">
        {media}
        {badge}
        <div class="deal-body">
          <div class="deal-cat">{icon} {cat}</div>
          <h3 class="deal-title">{title_html}</h3>
          <div class="deal-price-row">
            <span class="deal-price">{price}</span>
            {f'<span class="deal-mrp">{mrp}</span>' if mrp else ''}
            {rating_html}
          </div>
          <a class="btn btn-deal deal-cta" href="{href}" rel="nofollow sponsored noopener" target="_blank">View Deal →</a>
        </div>
      </article>"""

_IMG_DIMS_CACHE = {}


def _img_dims(rel_path):
    """Parse width/height from a local JPEG/PNG header -> (w, h) or (None, None)."""
    if rel_path in _IMG_DIMS_CACHE:
        return _IMG_DIMS_CACHE[rel_path]
    result = (None, None)
    try:
        data = (SITE_DIR / rel_path).read_bytes()
        if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
            result = (
                int.from_bytes(data[16:20], "big"),
                int.from_bytes(data[20:24], "big"),
            )
        elif data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                    result = (
                        int.from_bytes(data[i + 7:i + 9], "big"),
                        int.from_bytes(data[i + 5:i + 7], "big"),
                    )
                    break
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                if i + 4 > len(data):
                    break
                i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    except Exception:
        result = (None, None)
    _IMG_DIMS_CACHE[rel_path] = result
    return result


def head(title, desc, canonical, rel="", head_extra="", og_image=""):
    # og:image must be the page's own image (product pages -> real product photo,
    # so WhatsApp/Facebook/Telegram shares show the deal, not the generic logo).
    if og_image:
        og_img_url = BASE_URL + "/" + og_image.lstrip("/")
        iw, ih = _img_dims(og_image)
    else:
        og_img_url = BASE_URL + "/og-image.jpg"
        iw, ih = 1200, 630
    og_dim = (
        f'  <meta property="og:image:width" content="{iw}">\n'
        f'  <meta property="og:image:height" content="{ih}">\n'
        if iw and ih
        else ""
    )
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
  <meta property="og:image" content="{og_img_url}">
{og_dim}  <meta property="og:image:alt" content="{esc(title)}">
  <meta property="og:site_name" content="SmartGahr">
  <meta property="og:locale" content="en_IN">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{og_img_url}">
  <meta name="twitter:image:alt" content="{esc(title)}">
  <meta name="google-site-verification" content="kDpUhMVkIw8yo4plaH4RPhK0HuJbo_boNpSStxonc34" />
  <meta name="p:domain_verify" content="cf62f1ed7feba30bde14957942317589" />
  <link rel="stylesheet" href="{rel}style.css">
  <link rel="icon" type="image/svg+xml" href="{rel}favicon.svg">
  <link rel="apple-touch-icon" href="{rel}favicon.svg">
  {head_extra}
</head>"""

HEADER = """<header class="site-header">
  <div class="container">
    <a href="{home}" class="logo">Smart<span>Gahr</span></a>
    <nav class="nav">
      <a href="{home}">Home</a>
      <a href="{deals}">Deals</a>
      <a href="{diwali}">Diwali Sale</a>
      <a href="{bf}">Black Friday</a>
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
        <a href="{whatsapp}" rel="noopener">WhatsApp Channel</a>
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
        diwali=rel + "deals/diwali-sales/",
        bf=rel + "deals/black-friday/",
        about=rel + "about.html",
        contact=rel + "contact.html",
    )

def wa_share(page_url, lead=""):
    """WhatsApp share intent (wa.me) — opens the share picker with prefilled
    text + link. Free, no API. Visitor ke 1 tap = uske contacts tak forwarded."""
    return "https://wa.me/?text=" + quote((lead + " " + page_url).strip())


def build_footer(rel):
    return FOOTER.format(
        home=rel + "index.html",
        deals=rel + "deals/index.html",
        about=rel + "about.html",
        contact=rel + "contact.html",
        whatsapp=WHATSAPP_CHANNEL_URL,
        privacy=rel + "privacy.html",
        disclaimer=rel + "disclaimer.html",
    )

JSONLD_HOME = """<script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "SmartGahr",
    "url": "https://smartgahr.netlify.app/",
    "description": "Hand-checked Amazon India deals with real price drops and 4★+ ratings \u2014 every under \u20b9999 pick is 40%+ off. Prices verified daily.",
    "publisher": {
      "@type": "Organization",
      "name": "SmartGahr",
      "url": "https://smartgahr.netlify.app/",
      "sameAs": ["https://t.me/smartgahr", "https://whatsapp.com/channel/0029VbA209B17EmmO7QhYe0w"]
    }
  }
  </script>"""


HOME_FAQ = [
    (
        "Kya yahan sirf ₹999 se saste deals hain?",
        "Nahi. Site pe sabhi verified deals hain — ₹149 ke budget picks se lekar ₹29,999 tak ke premium "
        "products. Deals page pe \"₹999 se kam\" filter se sirf budget wale dekh sakte ho. Hum price range "
        "chhupate nahi, taaki click karke disappointment na ho.",
    ),
    (
        "Yeh Amazon deals sach mein verified hain?",
        "Haan. Har deal ka price, MRP, rating aur discount Amazon ke live product page se aata hai. ₹999 se kam "
        "wale budget picks pe 40%+ off hona zaroori hai; premium products sirf tab list karte hain jab price "
        "genuinely giro — inflated MRP wale jhoothe \"90% off\" offers hum publish nahi karte.",
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
    doc = f"""{head('SmartGahr — Verified Amazon Deals, 4★+ Rated', 'Hand-checked Amazon India deals with real price drops and 4★+ ratings — every under-₹999 pick is 40%+ off. Prices verified daily, expired deals removed.', BASE_URL + '/', head_extra=schema)}
<body>
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header('')}
<main>
  <section class="hero">
    <div class="container">
      <h1>🔥 Today's Best Amazon Deals — Verified, 4★+ Rated</h1>
      <p>₹149 se ₹29,999 tak. ₹999 se kam har deal 40%+ off; premium gear sirf jab price sach mein giro. 4★+ rating, no fake MRP.</p>
      <p class="updated">Last updated: {BUILT_DATE_HUMAN} · {len(products)} live deals</p>
      <div class="cta-row">
        <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Join Telegram Channel</a>
        <a class="btn btn-outline" href="deals/index.html">Browse All Deals</a>
        <a class="btn btn-wa" href="{wa_share(BASE_URL + '/', 'SmartGahr — ' + str(len(products)) + ' verified Amazon deals (4★+), roz update:')}" rel="noopener nofollow" target="_blank">Share on WhatsApp</a>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="channel-band">
        <h2>🖤 Black Friday Sale 2026 — 27 Nov | Flipkart, Myntra & AJIO</h2>
        <p>November ki sabse badi sale ke verified links ek jagah — electronics se winter fashion tak.</p>
        <a class="btn btn-deal" href="deals/black-friday/">Check Black Friday Sale →</a>
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
    jump_chips = []
    for cat in sorted(by_cat, key=lambda c: (-len(by_cat[c]), c)):
        slug = category_meta(cat)["slug"]
        items = sorted(by_cat[cat], key=discount_num, reverse=True)
        cards = "\n".join(
            deal_card(p, "../", pid=f"{slug}-{slugify(p.get('name'))}") for p in items
        )
        heading = f'{CATEGORY_ICONS.get(cat, chr(128722))} {esc(cat)}'
        if cat in page_cats:
            heading = f'<a href="{slug}/">{heading}</a>'
        jump_chips.append(
            f'<a class="chip" href="#{slugify(cat)}">{CATEGORY_ICONS.get(cat, chr(128722))} '
            f"{esc(cat)} ({len(items)})</a>"
        )
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
    cheap = sum(1 for p in products if 0 < price_num(p) <= 999)
    doc = f"""{head('All Verified Amazon Deals — 4★+ Rated | SmartGahr', f'All {len(products)} verified Amazon India deals in one place — 4★+ ratings, real price drops, every under-₹999 pick 40%+ off. Filter by budget or category.', BASE_URL + '/deals/', rel='../', head_extra=schema)}
<body id="top">
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header('../')}
<main>
  <section class="hero">
    <div class="container">
      <h1>🛒 All Verified Deals</h1>
      <p>{len(products)} live deals — sab 4★+ rated, real price drops. ₹149 se ₹29,999 tak; ₹999 se kam wale sab 40%+ off. Category pe jump karo ya budget filter chalao.</p>
      <p class="updated">Last updated: {BUILT_DATE_HUMAN}</p>
      <div class="chips hero-chips budget-chips" role="group" aria-label="Price filter">
        <button class="chip is-active" type="button" data-price-filter="">Sab deals ({len(products)})</button>
        <button class="chip" type="button" data-price-filter="999">₹999 se kam ({cheap})</button>
      </div>
      <div class="chips hero-chips">
        {"".join(jump_chips)}
      </div>
      <p class="filter-note" aria-live="polite"></p>
    </div>
  </section>
  <section class="section">
    <div class="container">
      <div class="channel-band">
        <h2>🖤 Black Friday Sale 2026 — 27 Nov | Flipkart, Myntra & AJIO</h2>
        <p>Amazon ke alawa November ki sabse badi sale ke verified links bhi yahin se — compare karke sasta pakdo.</p>
        <a class="btn btn-deal" href="black-friday/">Check Black Friday Sale →</a>
      </div>
    </div>
  </section>
{body}
  <section class="section">
    <div class="container">
      <div class="section-head"><h2>🛒 How to Choose the Right Deal</h2></div>
      <div class="deal-grid" style="grid-template-columns:1fr;">
        <div class="deal-card" style="padding:20px;">
          <div class="deal-body">
            <h3 class="deal-title">Budget vs Premium — Kya Kharidein?</h3>
            <p style="font-size:0.95rem;color:var(--muted);line-height:1.6;">
              <b>Under ₹999:</b> Earbuds, smartwatches, power banks, kitchen tools — daily use items jahan 40%+ discount mile. 
              <b>Premium (₹5K-30K):</b> Sony headphones, Redmi TV, Atomberg fan — long-term investment items jahan even 10-35% discount substantial savings dete hain.
            </p>
            <p style="font-size:0.95rem;color:var(--muted);line-height:1.6;">
              <b>Rule:</b> Budget pick (₹999 se kam) mein 40%+ off zaroori hai. Premium mein price history check karo — 
              Amazon ke prices har ghante badalte hain, isliye "lowest price" pe hi order karo.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
  <section class="section">
    <div class="container">
      <div class="channel-band">
        <h2>📲 Roj naye deals Telegram par</h2>
        <p>Sabse tez deals paane ke liye channel join karo.</p>
        <div class="cta-row">
          <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Join @smartgahr Free</a>
          <a class="btn btn-wa" href="{wa_share(BASE_URL + '/deals/', str(len(products)) + ' verified Amazon deals ek jagah — 4★+ rated, roz update:')}" rel="noopener nofollow" target="_blank">Share on WhatsApp</a>
        </div>
      </div>
    </div>
  </section>
</main>
  <p class="to-top"><a href="#top">↑ Back to top</a></p>
{FILTER_JS}
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
        crumb = (
            f'<nav class="breadcrumb" aria-label="Breadcrumb">'
            f'<a href="{rel}index.html">Home</a> <span aria-hidden="true">›</span> '
            f'<a href="../">All Deals</a> <span aria-hidden="true">›</span> '
            f"<span>{esc(cat)}</span></nav>"
        )
        doc = f"""{head(meta["title"], meta["desc"], page_url, rel=rel, head_extra=schema)}
<body id="top">
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header(rel)}
<main>
  <section class="hero">
    <div class="container">
      {crumb}
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
  <p class="to-top"><a href="#top">↑ Back to top</a></p>
{build_footer(rel)}
</body>
</html>
"""
        out_dir = DEALS_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(doc, encoding="utf-8")
        built.append(f"/deals/{slug}/")

    return built


DIWALI_LINKS = [
    (
        "https://fktr.in/ep5oHxG",
        "\U0001F6CD️",
        "Flipkart — Diwali Offers & Top Deals",
        "Electronics, appliances aur home & kitchen ke festive deals — Flipkart ka Offer Zone, jahan roz naye discount aate hain.",
    ),
    (
        "https://fktr.in/HomR51o",
        "\U0001F6D2",
        "Flipkart — Poora Store",
        "Fashion, home aur daily essentials samet poora Flipkart festive catalogue ek click me.",
    ),
    (
        "https://myntr.it/pI776ZO",
        "\U0001F457",
        "Myntra — Diwali Fashion Sale",
        "Ethnic wear, kurta sets, festive outfits aur footwear — fashion ke sabse tez girti hui festive prices.",
    ),
    (
        "https://ajiio.in/8L3K4Wi",
        "\U0001F3F7️",
        "AJIO — Diwali Sale",
        "Branded fashion & lifestyle pe festive offers — Diwali outfit aur gifting ke liye sasta option.",
    ),
]

DIWALI_FAQ = [
    (
        "Diwali sale kab tak chalta hai?",
        "Festive season ka main sale Diwali (8 November 2026) ke aas-paas chalta hai — Flipkart aur Amazon ke "
        "bade Diwali sales October se November tak aate hain, aur uske baad clearance offers bhi chalte rehte hain. "
        "Har sale page pe live dates aur last-minute deals milti hain.",
    ),
    (
        "In links se khareedne pe price alag hota hai?",
        "Bilkul nahi. Link pe click karne se aap retailer ke normal page pe pahunchte ho — wahi price, wahi offers. "
        "Affiliate commission humein retailer se milti hai; buyer se kuch extra nahi liya jata.",
    ),
    (
        "Flipkart aur Myntra — kahan sasta milega?",
        "Category pe depend karta hai: electronics aur appliances me aam taur pe Flipkart better rehta hai, jabki "
        "festive fashion (ethnic wear, kurta sets, footwear) me Myntra aur AJIO ke offers tez girti hain. Do page "
        "kholkar compare karna sabse sasta deal pakadne ka asli tareeka hai.",
    ),
    (
        "Kya SmartGahr sirf Amazon deals dikhata hai?",
        "Amazon ki verified deals hamara core hain — 59+ live deals, sab 4★+ rated, unhe All Deals page pe dekho. "
        "Yeh page Diwali ke Flipkart, Myntra aur AJIO sales ke liye hai, taaki festive shopping sabse saste ho.",
    ),
]


def build_diwali_page(products):
    """Diwali retail-sale landing page with Flipkart/Myntra/AJIO affiliate links."""
    page_url = BASE_URL + "/deals/diwali-sales/"
    rel = "../../"
    page_cats = categories_with_pages(products)
    chips = "".join(
        f'<a class="chip" href="../../{category_path(c)}">'
        f'{CATEGORY_ICONS.get(c, chr(128722))} {esc(c)}</a>'
        for c in sorted(page_cats)
    )
    cards = "\n".join(
        f"""  <div class="deal-card" style="padding:20px;">
    <div class="deal-body">
      <h3 class="deal-title">{icon} {esc(name)}</h3>
      <p style="font-size:0.95rem;color:var(--muted);line-height:1.6;">{esc(desc)}</p>
      <a class="btn btn-deal deal-cta" href="{href}" rel="nofollow sponsored noopener" target="_blank">Sale pe jao →</a>
    </div>
  </div>"""
        for href, icon, name, desc in DIWALI_LINKS
    )
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "All Deals", "item": BASE_URL + "/deals/"},
            {"@type": "ListItem", "position": 3, "name": "Diwali Sales", "item": page_url},
        ],
    }
    schema = "\n  ".join([jsonld(breadcrumb), jsonld(faq_schema(DIWALI_FAQ))])
    doc = f"""{head('Diwali Sales 2026 — Flipkart, Myntra & AJIO | SmartGahr', 'Diwali Sales 2026 ke verified sale links — Flipkart, Myntra aur AJIO ke festive offers ek jagah. Real discounts, no fake MRP — Diwali shopping yahan se shuru karo.', page_url, rel=rel, head_extra=schema)}
<body id="top">
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header(rel)}
<main>
  <section class="hero">
    <div class="container">
      <nav class="breadcrumb" aria-label="Breadcrumb"><a href="../../index.html">Home</a> <span aria-hidden="true">›</span> <a href="../">All Deals</a> <span aria-hidden="true">›</span> <span>Diwali Sales</span></nav>
      <h1>🧨 Diwali Sales 2026 — Flipkart, Myntra & AJIO</h1>
      <p>Diwali (8 November 2026) ke festive sales ke verified links — electronics aur home ke liye Flipkart, festive fashion ke liye Myntra aur AJIO. Sab kuch ek jagah, bina fake MRP ke.</p>
      <p>Prices daily change hote hain — sale page kholte hi current price check kar lena. Dono platform kholkar compare karna sabse sasta deal pakadne ka asli tareeka hai.</p>
      <div class="cta-row">
        <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Get Deals on Telegram</a>
        <a class="btn btn-outline" href="../">Amazon Deals →</a>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head">
        <h2>🏬 Diwali Sale Links</h2>
        <a href="../">Amazon deals →</a>
      </div>
      <div class="deal-grid">
{cards}
      </div>
      <p class="updated" style="text-align:center;">Disclosure: is page ke retail links affiliate hain — aapke price pe koi fark nahi padta, commission humein retailer se milta hai.</p>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head"><h2>🗂️ Verified Amazon deals bhi dekh lo</h2></div>
      <div class="chips">{chips}</div>
    </div>
  </section>

{faq_block(DIWALI_FAQ, "Diwali sales ke baare mein sawaal")}
</main>
  <p class="to-top"><a href="#top">↑ Back to top</a></p>
{build_footer(rel)}
</body>
</html>
"""
    out_dir = SITE_DIR / "deals" / "diwali-sales"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(doc, encoding="utf-8")


BF_LINKS = [
    (
        "https://fktr.in/ep5oHxG",
        "\U0001F525",
        "Flipkart — Black Friday Deals",
        "Electronics, appliances aur gadgets pe November ki sabse tez girti prices — Flipkart ka Black Friday hub.",
    ),
    (
        "https://fktr.in/HomR51o",
        "\U0001F6D2",
        "Flipkart — Poora Store",
        "Fashion, home aur daily essentials samet poora Flipkart catalogue ek click me — BF prices ke saath.",
    ),
    (
        "https://myntr.it/pI776ZO",
        "\U0001F457",
        "Myntra — Black Friday Fashion Sale",
        "Winter wear, jackets, ethnic aur footwear — Myntra pe Black Friday me fashion sabse tez girta hai.",
    ),
    (
        "https://ajiio.in/8L3K4Wi",
        "\U0001F3F7️",
        "AJIO — Black Friday Sale",
        "Branded fashion & lifestyle pe Black Friday offers — premium brands pe deep discounts.",
    ),
]

BF_FAQ = [
    (
        "Black Friday 2026 kab hai?",
        "Black Friday 2026 = 27 November 2026 (Friday), uske saath Cyber Monday 30 November. "
        "India me Flipkart, Myntra, AJIO aur Amazon ye sale 24-30 November tak chalti hai — "
        "aur pehli wave (24-26 November) me often best prices milte hain, kyunki stock limited hota hai.",
    ),
    (
        "In links se khareedne pe price alag hota hai?",
        "Bilkul nahi. Link pe click karne se aap retailer ke normal page pe pahunchte ho — wahi price, wahi offers. "
        "Affiliate commission humein retailer se milti hai; buyer se kuch extra nahi liya jata.",
    ),
    (
        "Flipkart aur Myntra — Black Friday pe kahan sasta milega?",
        "Category pe depend karta hai: electronics, appliances aur gadgets me Flipkart better rehta hai, jabki "
        "fashion (jackets, winter wear, ethnic, footwear) me Myntra aur AJIO ke offers tez girti hain. Do page "
        "kholkar compare karna sabse sasta deal pakadne ka asli tareeka hai.",
    ),
    (
        "Kya SmartGahr sirf Amazon deals dikhata hai?",
        "Amazon ki verified deals hamara core hain — 59+ live deals, sab 4★+ rated, unhe All Deals page pe dekho. "
        "Yeh page Black Friday ke Flipkart, Myntra aur AJIO sales ke liye hai, taaki November shopping sabse saste ho.",
    ),
]


def build_blackfriday_page(products):
    """Black Friday retail-sale landing page with Flipkart/Myntra/AJIO affiliate links."""
    page_url = BASE_URL + "/deals/black-friday/"
    rel = "../../"
    page_cats = categories_with_pages(products)
    chips = "".join(
        f'<a class="chip" href="../../{category_path(c)}">'
        f'{CATEGORY_ICONS.get(c, chr(128722))} {esc(c)}</a>'
        for c in sorted(page_cats)
    )
    cards = "\n".join(
        f"""  <div class="deal-card" style="padding:20px;">
    <div class="deal-body">
      <h3 class="deal-title">{icon} {esc(name)}</h3>
      <p style="font-size:0.95rem;color:var(--muted);line-height:1.6;">{esc(desc)}</p>
      <a class="btn btn-deal deal-cta" href="{href}" rel="nofollow sponsored noopener" target="_blank">Sale pe jao →</a>
    </div>
  </div>"""
        for href, icon, name, desc in BF_LINKS
    )
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "All Deals", "item": BASE_URL + "/deals/"},
            {"@type": "ListItem", "position": 3, "name": "Black Friday", "item": page_url},
        ],
    }
    schema = "\n  ".join([jsonld(breadcrumb), jsonld(faq_schema(BF_FAQ))])
    doc = f"""{head('Black Friday Sale 2026 India (27 Nov) — Flipkart, Myntra & AJIO | SmartGahr', 'Black Friday Sale 2026 India ke verified links — 27 November ko Flipkart, Myntra aur AJIO ke best offers ek jagah. Real discounts, no fake MRP — Black Friday shopping yahan se shuru karo.', page_url, rel=rel, head_extra=schema)}
<body id="top">
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header(rel)}
<main>
  <section class="hero">
    <div class="container">
      <nav class="breadcrumb" aria-label="Breadcrumb"><a href="../../index.html">Home</a> <span aria-hidden="true">›</span> <a href="../">All Deals</a> <span aria-hidden="true">›</span> <span>Black Friday</span></nav>
      <h1>🖤 Black Friday Sale 2026 India — 27 November</h1>
      <p>Black Friday 2026 (27 November) ke verified sale links — electronics aur gadgets ke liye Flipkart, fashion ke liye Myntra aur AJIO. Sab kuch ek jagah, bina fake MRP ke.</p>
      <p>Sale 24-30 November waves me chalti hai — prices daily change hote hain, page kholte hi current price check kar lena. Do platform kholkar compare karna sabse sasta deal pakadne ka asli tareeka hai.</p>
      <div class="cta-row">
        <a class="btn btn-telegram" href="{CHANNEL_URL}" rel="noopener">Get Deals on Telegram</a>
        <a class="btn btn-outline" href="../">Amazon Deals →</a>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head">
        <h2>🏬 Black Friday Sale Links</h2>
        <a href="../">Amazon deals →</a>
      </div>
      <div class="deal-grid">
{cards}
      </div>
      <p class="updated" style="text-align:center;">Disclosure: is page ke retail links affiliate hain — aapke price pe koi fark nahi padta, commission humein retailer se milta hai.</p>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head"><h2>🗂️ Verified Amazon deals bhi dekh lo</h2></div>
      <div class="chips">{chips}</div>
    </div>
  </section>

{faq_block(BF_FAQ, "Black Friday sales ke baare mein sawaal")}
</main>
  <p class="to-top"><a href="#top">↑ Back to top</a></p>
{build_footer(rel)}
</body>
</html>
"""
    out_dir = SITE_DIR / "deals" / "black-friday"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(doc, encoding="utf-8")


_OG_VERSION = "2"  # bump when the card design changes (invalidates og/*.jpg cache)


def make_og_image(name, price, mrp, disc, rating, rc, img_rel, slug):
    """1200x630 share card (product photo + price + brand) for WhatsApp/FB/Twitter
    previews. Raw product photos are square/portrait and get centre-cropped to
    1.91:1 — this canvas keeps the product intact and shows the price.
    Returns site-relative path ('og/<slug>.jpg') or None -> caller falls back."""
    if not img_rel or not slug:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    safe_slug = re.sub(r"[^a-z0-9-]", "-", slug.lower()).strip("-")
    if not safe_slug:
        return None
    out_rel = f"og/{safe_slug}.jpg"
    src, out = SITE_DIR / img_rel, SITE_DIR / out_rel
    try:
        if not src.exists():
            return None
        try:
            ver = (SITE_DIR / "og" / ".version").read_text(encoding="utf-8").strip()
        except Exception:
            ver = ""
        if ver == _OG_VERSION and out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
            return out_rel

        def font(size, bold=True):
            paths = (
                [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
                if bold
                else [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"]
            )
            for fp in paths:
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        f_brand, f_name = font(44), font(46)
        f_price, f_small, f_badge, f_foot = font(74), font(30), font(26, False), font(26, False)

        def ok(fnt, ch):
            try:
                return fnt.getbbox(ch)[2] > fnt.getbbox("\ue123")[2] or fnt.getbbox(ch) != fnt.getbbox("\ue123")
            except Exception:
                return False

        def clean(text):
            text = re.sub(r"\s+", " ", str(text or "")).strip()
            for ch, alt in (("₹", "Rs. "), ("★", "")):
                if ch in text and not ok(f_price, ch):
                    text = text.replace(ch, alt)
            return text

        W, H = 1200, 630
        canvas = Image.new("RGB", (W, H), "#ffffff")
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, 0, W, 14], fill="#4f46e5")                     # brand bar
        d.rounded_rectangle([40, 54, 500, 586], radius=18, fill="#f6f7fb", outline="#e5e7eb", width=2)

        # product photo: contain inside the left panel (never crop)
        try:
            ph = Image.open(src)
            ph = ph.convert("RGB")
            bw, bh = 412, 484
            scale = min(bw / ph.width, bh / ph.height)
            ph = ph.resize((max(1, int(ph.width * scale)), max(1, int(ph.height * scale))), Image.LANCZOS)
            canvas.paste(ph, (40 + (460 - ph.width) // 2, 54 + (532 - ph.height) // 2))
        except Exception:
            pass

        x0, x1 = 540, 1160
        d.text((x0, 66), "SmartGahr", font=f_brand, fill="#4f46e5")
        d.text((x1, 76), "PRICE VERIFIED · 4.0+ RATED", font=f_badge, fill="#047857", anchor="ra")

        # product name (max 3 lines)
        words, lines, cur = clean(name).split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textbbox((0, 0), t, font=f_name)[2] <= x1 - x0:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1].rstrip(" ,—-") + "…"
        y = 138
        for ln in lines:
            d.text((x0, y), ln, font=f_name, fill="#0f172a")
            y += 56
        y += 26

        # price + struck MRP + % off badge
        price_t, mrp_t = clean(price), clean(mrp)
        if price_t:
            d.text((x0, y), price_t, font=f_price, fill="#047857")
            pw = d.textbbox((0, 0), price_t, font=f_price)[2]
            if mrp_t and mrp_t != price_t:
                mx = x0 + pw + 26
                d.text((mx, y + 40), mrp_t, font=f_small, fill="#64748b")
                mw = d.textbbox((0, 0), mrp_t, font=f_small)[2]
                d.line([mx, y + 56, mx + mw, y + 56], fill="#64748b", width=2)
            if disc:
                bx = x0 + pw + 26 + (d.textbbox((0, 0), mrp_t, font=f_small)[2] + 26 if mrp_t and mrp_t != price_t else 0)
                bt = f"{disc}% OFF"
                bw2 = d.textbbox((0, 0), bt, font=f_badge)[2] + 28
                if bx + bw2 <= x1:
                    d.rounded_rectangle([bx, y + 18, bx + bw2, y + 66], radius=10, fill="#f59e0b")
                    d.text((bx + 14, y + 28), bt, font=f_badge, fill="#ffffff")
            y += 104

        # rating line
        if rating:
            rt = f"{rating}/5" + (f"  ·  {int(rc):,} ratings" if rc else "  ·  verified rating")
            d.text((x0, y), clean(rt), font=f_small, fill="#b45309")
            y += 50

        # footer
        d.text((x0, 556), "smartgahr.netlify.app", font=f_foot, fill="#64748b")
        d.ellipse([x0 - 22, 563, x0 - 8, 577], fill="#f59e0b")

        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out, "JPEG", quality=86, optimize=True)
        return out_rel
    except Exception:
        return None


def build_product_pages(products, page_cats):
    """One indexable page per deal: unique copy, Product + Breadcrumb schema,
    related-deals internal links. Returns [(url_path, image_file_or_None)]."""
    rel = "../../../"
    built = []
    by_cat = {}
    for p in products:
        by_cat.setdefault(p.get("category") or "Deals", []).append(p)

    for p in products:
        link = (p.get("link") or "").strip()
        path = PRODUCT_PATHS.get(link)
        if not path:
            continue
        cat = p.get("category") or "Deals"
        meta = category_meta(cat)
        icon = CATEGORY_ICONS.get(cat, "\U0001F6D2")
        url = f"{BASE_URL}/{path}"
        name = p.get("name") or "Amazon Deal"
        hook = (p.get("hook") or "").strip()
        fix = (p.get("fix") or "").strip()
        pain = (p.get("pain") or "").strip()
        loot = (p.get("loot_reason") or "").strip()
        price = p.get("price") or ""
        mrp = p.get("mrp") or ""
        rating = p.get("rating")
        disc = discount_num(p)
        img = product_image(link)
        px = price_num(p)

        desc_src = (hook + " " + fix).strip() or (
            f"{name} — verified Amazon India deal at {price}"
            + (f" ({disc}% off MRP)." if disc else ".")
        )
        desc = re.sub(r"\s+", " ", desc_src)
        if len(desc) < 110:
            pad = f" {name} — verified Amazon India deal, real price drop and 4★+ rating."
            desc = (desc + pad)[:155]
        else:
            desc = desc[:155]

        # Title <= 60 chars (Google/Ahrefs truncation limit); long names drop price tail.
        suffix_full = f" at {price}" + (f" — {disc}% Off" if disc else "") + " | SmartGahr"
        suffix_min = " | SmartGahr"
        if len(name) + len(suffix_full) <= 60:
            title = name + suffix_full
        else:
            budget = 60 - len(suffix_min) - 1
            cut = name[:budget]
            sp = cut.rfind(" ")
            if sp > 25:
                cut = cut[:sp]
            title = cut.rstrip(" ,—-") + "…" + suffix_min
        rc = p.get("rating_count")
        rating_html = (
            f'<span class="deal-rating">⭐ {esc(rating)}/5{f" ({int(rc):,})" if rc else ""}</span>'
            if rating else ""
        )
        img_html = (
            f'<div class="deal-media"><img src="{rel}{img}" alt="{esc(name)}" '
            f'width="300" height="300" loading="eager" decoding="async"></div>'
            if img
            else ""
        )
        go_href = rel + deal_href(link)

        # Product + Breadcrumb structured data (rich-result eligible)
        prod_schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "description": desc,
            "image": (BASE_URL + "/" + img) if img else BASE_URL + "/og-image.jpg",
            "brand": {"@type": "Brand", "name": schema_brand(name)},
            "offers": {
                "@type": "Offer",
                "priceCurrency": "INR",
                "price": str(px),
                "url": url,
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
                "hasMerchantReturnPolicy": {
                    "@type": "MerchantReturnPolicy",
                    "applicableCountry": "IN",
                    "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                    "merchantReturnDays": 10,
                    "returnMethod": "https://schema.org/ReturnByMail",
                    "returnFees": "https://schema.org/FreeReturn",
                },
                "shippingDetails": {
                    "@type": "OfferShippingDetails",
                    "shippingRate": {
                        "@type": "MonetaryAmount",
                        "value": "0",
                        "currency": "INR",
                    },
                    "shippingDestination": {
                        "@type": "DefinedRegion",
                        "addressCountry": "IN",
                    },
                    "deliveryTime": {
                        "@type": "ShippingDeliveryTime",
                        "handlingTime": {
                            "@type": "QuantitativeValue",
                            "minValue": 0,
                            "maxValue": 1,
                            "unitCode": "DAY",
                        },
                        "transitTime": {
                            "@type": "QuantitativeValue",
                            "minValue": 1,
                            "maxValue": 7,
                            "unitCode": "DAY",
                        },
                    },
                },
            },
        }
        if rating:
            agg = {
                "@type": "AggregateRating",
                "ratingValue": str(rating),
                "bestRating": "5",
                "worstRating": "1",
            }
            if p.get("rating_count"):
                agg["ratingCount"] = str(p["rating_count"])
            prod_schema["aggregateRating"] = agg
        cat_url = (BASE_URL + "/" + category_path(cat)) if cat in page_cats else BASE_URL + "/deals/"
        breadcrumb = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": "All Deals", "item": BASE_URL + "/deals/"},
                {"@type": "ListItem", "position": 3, "name": cat, "item": cat_url},
                {"@type": "ListItem", "position": 4, "name": name, "item": url},
            ],
        }
        schema = jsonld(prod_schema) + "\n  " + jsonld(breadcrumb)

        cat_href = rel + (category_path(cat) if cat in page_cats else "deals/")
        crumb = (
            f'<nav class="breadcrumb" aria-label="Breadcrumb">'
            f'<a href="{rel}index.html">Home</a> <span aria-hidden="true">›</span> '
            f'<a href="{rel}deals/">All Deals</a> <span aria-hidden="true">›</span> '
            f'<a href="{cat_href}">{esc(cat)}</a> <span aria-hidden="true">›</span> '
            f"<span>{esc(name[:60])}</span></nav>"
        )

        others = sorted(
            (q for q in by_cat.get(cat, []) if q is not p),
            key=discount_num, reverse=True,
        )[:6]
        related = "\n".join(deal_card(q, rel) for q in others)
        related_html = (
            f"""  <section class="section">
    <div class="container">
      <div class="section-head">
        <h2>More {esc(cat)} deals</h2>
        <a href="{rel}deals/">View everything →</a>
      </div>
      <div class="deal-grid">
{related}
      </div>
    </div>
  </section>"""
            if related
            else ""
        )

        body_paras = "\n".join(
            f"      <p>{esc(t)}</p>" for t in (pain, fix, loot) if t
        )
        og_rel = make_og_image(
            name, price, mrp, disc, rating, p.get("rating_count"), img,
            (path or "").rstrip("/").split("/")[-1],
        )
        doc = f"""{head(title, desc, url, rel=rel, head_extra=schema, og_image=og_rel or img or "")}
<body id="top">
<!-- generated by _site_builder.py — do not edit by hand -->
{build_header(rel)}
<main>
  <section class="hero">
    <div class="container">
      {crumb}
      <div class="product-top">
        {img_html}
        <div class="product-info">
          <div class="deal-cat">{icon} {esc(cat)}</div>
          <h1>{esc(name)}</h1>
          <div class="deal-price-row">
            <span class="deal-price deal-price-lg">{esc(price)}</span>
            {f'<span class="deal-mrp">{esc(mrp)}</span>' if mrp else ''}
            {rating_html}
          </div>
          <a class="btn btn-deal deal-cta" href="{go_href}" rel="nofollow sponsored noopener" target="_blank">View on Amazon →</a>
          <p class="updated">Verified price · Updated {BUILT_DATE_HUMAN}{" · " + str(disc) + "% off MRP" if disc else ""}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="section-head"><h2>{esc(hook) if hook else esc(name)}</h2></div>
{body_paras}
      <div class="cta-row">
        <a class="btn btn-deal" href="{go_href}" rel="nofollow sponsored noopener" target="_blank">Check Live Price on Amazon →</a>
        <a class="btn btn-outline" href="{cat_href}">More {esc(cat)} deals</a>
        <a class="btn btn-wa" href="{wa_share(url, 'Deal: ' + name + ' at ' + str(price) + ' —')}" rel="noopener nofollow" target="_blank">Share on WhatsApp</a>
      </div>
    </div>
  </section>

{related_html}
</main>
  <p class="to-top"><a href="#top">↑ Back to top</a></p>
{build_footer(rel)}
</body>
</html>
"""
        out_dir = SITE_DIR / path
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(doc, encoding="utf-8")
        built.append(("/" + path, img))

    # every card is now this design version -> mark the og/ cache valid
    try:
        og_dir = SITE_DIR / "og"
        og_dir.mkdir(parents=True, exist_ok=True)
        (og_dir / ".version").write_text(_OG_VERSION, encoding="utf-8")
    except Exception:
        pass

    return built


def build_sitemap(extra_urls=(), products=(), product_pages=()):
    """Single sitemap: all pages + product images (Google reads one file, fewer failures)."""
    urls = [
        ("/", "1.0"),
        ("/deals/", "0.9"),
        ("/deals/diwali-sales/", "0.9"),
        ("/deals/black-friday/", "0.9"),
        *[(u, "0.8") for u in extra_urls],
        *[(u, "0.7") for u, _ in product_pages],
        ("/about.html", "0.3"),
        ("/contact.html", "0.3"),
        ("/privacy.html", "0.2"),
        ("/disclaimer.html", "0.2"),
    ]

    def img_entry(file_rel, name):
        return (
            f"    <image:image>\n"
            f"      <image:loc>{BASE_URL}/{file_rel}</image:loc>\n"
            f"      <image:title>{name}</image:title>\n"
            f"      <image:caption>{name} — verified Amazon India deal</image:caption>\n"
            f"    </image:image>"
        )

    images = load_images()
    image_entries = []
    for p in products:
        file_rel = images.get((p.get("link") or "").strip())
        if not file_rel:
            continue
        name = esc(p.get("name") or "Amazon deal")
        image_entries.append(img_entry(file_rel, name))
    path_names = {
        "/" + path: esc(p.get("name") or "Amazon deal")
        for p in products
        for path in [PRODUCT_PATHS.get((p.get("link") or "").strip())]
        if path
    }
    product_images = {
        u: img_entry(f, path_names.get(u, "Amazon deal"))
        for u, f in product_pages if f
    }

    entries = "\n".join(
        f"  <url>\n    <loc>{BASE_URL}{u}</loc>\n    <lastmod>{BUILT_DATE}</lastmod>\n"
        f"    <priority>{pr}</priority>\n"
        + (
            (chr(10).join(image_entries) + "\n" if u == "/deals/" and image_entries else "")
            if u == "/deals/"
            else (product_images.get(u, "") + "\n" if u in product_images else "")
        )
        + "  </url>"
        for u, pr in urls
    )
    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
{entries}
</urlset>
"""
    (SITE_DIR / "sitemap.xml").write_text(doc, encoding="utf-8")
    return len(image_entries)


def cleanup_stale_product_pages():
    """Delete product page dirs no longer built (dormant rows, renamed slugs).

    Keeps category landing pages (deals/<cat>/index.html) and anything not a
    product page directory with its own index.html.
    """
    keep = {p.rstrip("/") for p in PRODUCT_PATHS.values()}
    removed = 0
    if not DEALS_DIR.exists():
        return 0
    for cat_dir in DEALS_DIR.iterdir():
        if not cat_dir.is_dir():
            continue
        for page_dir in cat_dir.iterdir():
            if not page_dir.is_dir() or not (page_dir / "index.html").exists():
                continue
            rel = page_dir.relative_to(SITE_DIR).as_posix()
            if rel not in keep:
                shutil.rmtree(page_dir)
                removed += 1
    return removed

def main():
    products = load_products()
    if not products:
        print("No products in product.json — skipping site build")
        return
    assign_product_paths(products)
    build_index(products)
    build_deals_page(products)
    build_diwali_page(products)
    build_blackfriday_page(products)
    page_cats = categories_with_pages(products)
    cats = build_category_pages(products)
    prod_pages = build_product_pages(products, page_cats)
    n_images = build_sitemap(cats, products, prod_pages)
    removed = cleanup_stale_product_pages()
    print(
        f"Site built: {len(products)} deals -> index.html, deals/index.html, "
        f"diwali-sales page, {len(cats)} category page(s), {len(prod_pages)} product page(s), "
        f"sitemap.xml ({n_images} images)"
        + (f", cleaned {removed} stale page(s)" if removed else "")
    )

if __name__ == "__main__":
    main()
