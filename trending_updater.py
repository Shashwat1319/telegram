import os
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from bs4 import BeautifulSoup
import requests, json, re, subprocess, time, random, sys, threading, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AFFILIATE_ID_IN = os.getenv("AFFILIATE_ID_IN", "shashwat022-21")
json_lock = threading.Lock()

CATEGORIES = [
    ("https://www.amazon.in/gp/movers-and-shakers/electronics", "Electronics"),
    ("https://www.amazon.in/gp/movers-and-shakers/kitchen", "Kitchen"),
    ("https://www.amazon.in/gp/movers-and-shakers/computers", "Computers & Accessories"),
    ("https://www.amazon.in/gp/movers-and-shakers/office-products", "Office Products"),
    ("https://www.amazon.in/gp/movers-and-shakers/shoes", "Shoes & Fashion"),
    ("https://www.amazon.in/gp/movers-and-shakers/home-improvement", "Home Improvement"),
    ("https://www.amazon.in/gp/movers-and-shakers/beauty", "Beauty & Personal Care"),
    ("https://www.amazon.in/gp/movers-and-shakers/toys", "Toys & Games"),
    ("https://www.amazon.in/gp/movers-and-shakers/sports", "Sports & Fitness"),
    ("https://www.amazon.in/gp/movers-and-shakers/automotive", "Automotive"),
    ("https://www.amazon.in/gp/goldbox", "Today's Deals"),
]

def get_amazon_trending(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200: return None
        if "captcha" in r.text.lower() or "api-services-support" in r.text: return None
        return r.text
    except:
        return None

def preprocess_html(html):
    if not html: return ""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        wrappers = soup.select('div[id^="gridItemRoot"]') or soup.select('.p13n-sc-uncentered-wrapper') or soup.select('.s-result-item')
        products = []
        for w in wrappers[:20]:
            name = w.select_one('.p13n-sc-truncate, .a-size-base-plus, h2, ._cDEzb_p13n-sc-css-line-clamp-3_g3dy1')
            price = w.select_one('.a-price-whole, .p13n-sc-price, ._cDEzb_p13n-sc-price_3mJ9Z')
            mrp = w.select_one('.a-text-strike')
            link = w.select_one('a.a-link-normal')
            img = w.select_one('img[data-a-dynamic-image], img[data-old-hires], img[src]')
            rating = w.select_one('i[class*="a-icon-star"] span.a-icon-alt, span[class*="a-icon-alt"]')

            p_image = ""
            if img:
                if img.has_attr('data-a-dynamic-image'):
                    try: p_image = list(json.loads(img['data-a-dynamic-image']).keys())[-1]
                    except: pass
                if not p_image and img.has_attr('data-old-hires'): p_image = img['data-old-hires']
                if not p_image and img.has_attr('src'):
                    src = img['src']
                    if not any(b in src for b in ["01jrA-8DXYL.gif", "transparent-pixel", "spacer.gif"]):
                        p_image = src
            if not p_image: continue

            products.append({
                "name": name.get_text(strip=True) if name else "",
                "price": price.get_text(strip=True) if price else "Check",
                "mrp": mrp.get_text(strip=True) if mrp else "",
                "rating": rating.get_text(strip=True) if rating else "Not specified",
                "image": p_image,
                "link": link['href'] if link and 'href' in link.attrs else "#"
            })
        return json.dumps(products, ensure_ascii=False)
    except:
        return ""

def extract_products_with_ai(html_text, retry=0):
    models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
    model = models[retry % len(models)] if retry else random.choice(models)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""You are a deal hunter for an Indian deals channel. From the JSON product data below, select the TOP 3 products that will get MAXIMUM CLICKS and SALES.

SELECTION CRITERIA (priority order):
1. HIGH DISCOUNT: 40%+ off is gold, 60%+ is must-pick
2. HIGH DEMAND: Trending products people actually search for
3. GOOD RATING: 4.0+ stars only
4. PRICE RANGE: ₹99 to ₹2000 (impulse to mid-range)
5. VISUAL APPEAL: Products with attractive images perform better

Return ONLY valid JSON array with these EXACT fields copied from input:
- "name", "price", "mrp", "rating", "image", "link" (COPY EXACTLY, DO NOT MODIFY)
PLUS add these new fields:
- "discount_percent": string like "65%"
- "hook": FOMO-driven Hinglish hook (max 10 words, make them click)
- "pain": relatable problem this solves
- "fix": why this is a steal deal in 1 sentence
- "loot_reason": why this price is amazing (e.g. "Ab tak ka lowest price!")

TONE VARIETY: Make the 3 products have different tones - one urgent, one practical, one exciting.

DATA: {html_text}"""

    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        res = r.json()
        if "error" in res:
            if res["error"]["code"] == 429 and retry < 3:
                time.sleep(15)
                return extract_products_with_ai(html_text, retry + 1)
            return []
        text = res['candidates'][0]['content']['parts'][0]['text']
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        products = json.loads(text)
        validated = []
        for p in products:
            try:
                ps = re.sub(r'[^\d.]', '', str(p.get('price', '0')))
                ms = re.sub(r'[^\d.]', '', str(p.get('mrp', '0')))
                pv = float(ps) if ps else 0
                mv = float(ms) if ms else 0
                if pv == 0 or (mv > 0 and pv >= mv): continue
                ds = str(p.get('discount_percent', '0')).replace('%', '')
                dv = float(re.search(r'\d+', ds).group()) if re.search(r'\d+', ds) else 0
                if dv > 98 or dv < 5: continue
                if pv < 99 or pv > 2000: continue
                p['price'] = f"₹{int(pv)}"
                if mv > 0: p['mrp'] = f"₹{int(mv)}"
                p['discount_percent'] = f"{int(dv)}%"
                validated.append(p)
            except: continue
        return validated
    except:
        return []

def clean_amazon_link(link, tag):
    if "url=" in link:
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
            if 'url' in qs: link = qs['url'][0]
        except: pass
    if "amzn.to" in link: return link
    asin = re.search(r'/(?:dp|gp/product|asin|d|product)/([A-Z0-9]{10})', link, re.IGNORECASE)
    if asin: return f"https://www.amazon.in/dp/{asin.group(1).upper()}?tag={tag}"
    if not link.startswith("http"): link = f"https://www.amazon.in{link if link.startswith('/') else '/' + link}"
    if "tag=" not in link: link += ("&" if "?" in link else "?") + f"tag={tag}"
    return link

def add_affiliate_tags(products):
    for p in products:
        p['link'] = clean_amazon_link(p.get('link', ''), AFFILIATE_ID_IN)
    return products

def update_json(new_products):
    fp = "product.json"
    data = {"products": []}
    if os.path.exists(fp):
        try: data = json.load(open(fp, "r", encoding="utf-8"))
        except: pass

    asin_pat = re.compile(r'/dp/([A-Z0-9]{10})', re.IGNORECASE)
    existing = {p['name'] for p in data['products']}
    existing_asins = set()
    for p in data['products']:
        m = asin_pat.search(p.get('link', ''))
        if m: existing_asins.add(m.group(1).upper())

    added = 0
    for p in new_products:
        img = p.get('image', '')
        if not img or 'PLACEHOLDER' in img: continue
        if p['name'] in existing: continue
        m = asin_pat.search(p.get('link', ''))
        asin = m.group(1).upper() if m else ''
        if not asin or asin in existing_asins: continue
        data['products'].insert(0, p)
        existing.add(p['name'])
        existing_asins.add(asin)
        added += 1
    data['products'] = data['products'][:200]
    with json_lock:
        json.dump(data, open(fp, "w", encoding="utf-8"), indent=4, ensure_ascii=False)
    print(f"Added {added} new products.")
    return added > 0

def main():
    print("=== Trending Products Sync ===")
    any_new = False
    with ThreadPoolExecutor(max_workers=5) as ex:
        def sync(url, name):
            print(f"[*] {name}...")
            html = get_amazon_trending(url)
            if not html: return False
            text = preprocess_html(html)
            if not text: return False
            products = extract_products_with_ai(text)
            if products:
                for p in products: p['category'] = name
                products = add_affiliate_tags(products)
                return update_json(products)
            return False
        results = [ex.submit(sync, u, n) for u, n in CATEGORIES]
        any_new = any(r.result() for r in results)

    if any_new:
        subprocess.run([sys.executable, "bot_post.py", "--dry-run"])
        subprocess.run([sys.executable, "auto_blogger.py"])
        subprocess.run([sys.executable, "fb_bot_post.py"])
    else:
        print("No new products. Posting random deals...")
        subprocess.run([sys.executable, "bot_post.py", "--dry-run", "--random"])
        subprocess.run([sys.executable, "fb_bot_post.py"])

    print("Sync complete.")

if __name__ == "__main__":
    main()
