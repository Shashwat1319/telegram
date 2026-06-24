import os, json, re, requests, logging
from datetime import datetime
from dotenv import load_dotenv

from utils import tracked_link, slugify, calc_discount, extract_asin

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BLOG_DIR = "website/src/content/blog"
DEAL_DIR = "website/src/content/deals"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def generate_deal_page(product):
    asin = extract_asin(product.get('link', '')) or slugify(product.get('name', ''))[:20]
    fp = os.path.join(DEAL_DIR, f"{asin}.md")
    if os.path.exists(fp): return False

    disc = calc_discount(product.get('price', '0'), product.get('mrp', '0'))
    name = product.get('name', 'Product').replace('"', "'")
    img = product.get('image', '')
    link = tracked_link(product.get('link', ''))
    cat = product.get('category', 'Deals')
    rating = product.get('rating', '')

    with open(fp, "w", encoding="utf-8") as f:
        f.write(f"""---
title: "{name}"
description: "Get {name} at just {product.get('price','')} - Save {disc}%! Verified Amazon deal."
pubDate: "{datetime.now().strftime('%Y-%m-%d')}"
price: "{product.get('price','')}"
mrp: "{product.get('mrp','')}"
discount: "{disc}%"
image: "{img}"
buyLink: "{link}"
category: "{cat}"
rating: "{rating}"
---

🔥 **{disc}% OFF** on {name}

💸 **Price**: ~~{product.get('mrp','')}~~ → **{product.get('price','')}**
⭐ **Rating**: {rating}

👉 **[Buy Now on Amazon]({link})**

### Why this deal?
{product.get('loot_reason', f'Amazing {disc}% discount. Grab it before price goes up!')}

### More deals?
Join **[@budgetdeals_india](https://t.me/budgetdeals_india)** on Telegram for daily loot!
""")
    return True

def generate_blog_post(product):
    if not GEMINI_API_KEY: return None
    asin = extract_asin(product.get('link', '')) or slugify(product.get('name', 'product'))[:20]
    fp = os.path.join(BLOG_DIR, f"{asin}.md")
    if os.path.exists(fp): return False

    name = product.get('name', 'Product').replace('"', "'")
    disc = calc_discount(product.get('price', '0'), product.get('mrp', '0'))
    link = tracked_link(product.get('link', ''))
    img = product.get('image', '')

    prompt = f"""Write a 200-300 word SEO blog post about this product for Indian shoppers.
Title: {name}
Price: {product.get('price','')}
MRP: {product.get('mrp','')}
Discount: {disc}%
Target keywords: best deals India, {name[:30]}, Amazon price drop, budget shopping

Write Hinglish-English. Include: catchy opening, 3 selling points, why this is a steal, CTA to join @budgetdeals_india on Telegram.

Return ONLY the blog text."""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30
        )
        content = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        content = f"Looking for {name} at the best price? Get it for just {product.get('price','')} - {disc}% off! This is a verified Amazon India deal with fast shipping. Join @budgetdeals_india on Telegram for daily deals!"

    with open(fp, "w", encoding="utf-8") as f:
        f.write(f"""---
title: "{name} @ Just {product.get('price','')} - Save {disc}%!"
description: "{name} at {disc}% off! Only {product.get('price','')}. Verified Amazon India deal."
pubDate: "{datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')}"
heroImage: "{img}"
buyLink: "{link}"
---

{content}

👉 **[Buy Now on Amazon]({link})**

📢 **Join [@budgetdeals_india](https://t.me/budgetdeals_india)** for daily deals!
""")
    return True

def main():
    os.makedirs(BLOG_DIR, exist_ok=True); os.makedirs(DEAL_DIR, exist_ok=True)
    if not os.path.exists("product.json"): log.warning("No product.json found"); return
    products = json.load(open("product.json", encoding="utf-8"))["products"]
    if not products: log.warning("No products in product.json"); return

    log.info("Generating content for %d products...", len(products))
    blogs = deals = 0
    for i, p in enumerate(products):
        if generate_deal_page(p): deals += 1
        if i < 5 and generate_blog_post(p): blogs += 1

    bcount = len(os.listdir(BLOG_DIR)) if os.path.isdir(BLOG_DIR) else 0
    dcount = len(os.listdir(DEAL_DIR)) if os.path.isdir(DEAL_DIR) else 0
    log.info("New: %d deals + %d blogs", deals, blogs)
    log.info("Total site: %d blogs + %d deals", bcount, dcount)

if __name__ == "__main__":
    main()
