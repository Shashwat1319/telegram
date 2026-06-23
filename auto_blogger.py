import os, json, re, requests
from datetime import datetime
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "")

BLOG_DIR = "website/src/content/blog"
DEAL_DIR = "website/src/content/deals"

def tracked_link(url):
    if not CLICK_TRACKER_URL: return url
    return f"{CLICK_TRACKER_URL}/go?url={quote(url)}"

def slugify(name):
    s = re.sub(r'[^\w\s-]', '', name.lower().replace("&", "and"))
    return re.sub(r'[-\s]+', '-', s).strip('-')[:80]

def generate_deal_page(product):
    asin = re.search(r'/dp/([A-Z0-9]{10})', product.get('link',''))
    asin = asin.group(1).lower() if asin else slugify(product['name'])[:20]
    fp = os.path.join(DEAL_DIR, f"{asin}.md")
    if os.path.exists(fp): return False

    pv = int(re.sub(r'[^\d]', '', str(product.get('price','0')))) or 0
    mv = int(re.sub(r'[^\d]', '', str(product.get('mrp','0')))) or 0
    disc = int(((mv - pv) / mv) * 100) if mv > pv else 0
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
    asin = re.search(r'/dp/([A-Z0-9]{10})', product.get('link',''))
    asin = asin.group(1).lower() if asin else slugify(product.get('name', 'product'))[:20]
    fp = os.path.join(BLOG_DIR, f"{asin}.md")
    if os.path.exists(fp): return False

    name = product.get('name', 'Product').replace('"', "'")
    pv = int(re.sub(r'[^\d]', '', str(product.get('price','0')))) or 0
    mv = int(re.sub(r'[^\d]', '', str(product.get('mrp','0')))) or 0
    disc = int(((mv - pv) / mv) * 100) if mv > pv else 0
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
    if not os.path.exists("product.json"): print("No product.json"); return
    products = json.load(open("product.json", encoding="utf-8"))["products"]
    if not products: print("No products"); return

    print(f"Generating content for {len(products)} products...")
    blogs = deals = 0
    for i, p in enumerate(products):
        if generate_deal_page(p): deals += 1
        if i < 5 and generate_blog_post(p): blogs += 1

    bcount = len(os.listdir(BLOG_DIR)) if os.path.isdir(BLOG_DIR) else 0
    dcount = len(os.listdir(DEAL_DIR)) if os.path.isdir(DEAL_DIR) else 0
    print(f"✅ New: {deals} deals + {blogs} blogs")
    print(f"📊 Total site: {bcount} blogs + {dcount} deals")

if __name__ == "__main__":
    main()
