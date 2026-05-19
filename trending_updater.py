import os
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from bs4 import BeautifulSoup

import requests
import json
import re
import subprocess
import time
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AFFILIATE_ID_IN = os.getenv("AFFILIATE_ID_IN")
AFFILIATE_ID_COM = os.getenv("AFFILIATE_ID_COM")

# Threading lock for safe JSON writing
json_lock = threading.Lock()

def get_amazon_trending(category_url):
    """Scrape Amazon India Movers & Shakers for a specific category."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(category_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch {category_url}: Status {response.status_code}")
            return None
        html = response.text
        print(f"Successfully fetched {category_url}. HTML Length: {len(html)}")
        if "api-services-support@amazon.com" in html or "captcha" in html.lower():
            print(f"⚠️ Warning: Amazon might be blocking this request (CAPTCHA/Bot Detection detected).")
        return html
    except Exception as e:
        print(f"Error scraping {category_url}: {e}")
        return None

def preprocess_html(html_content):
    """Extract structured product data as text to prevent AI hallucination."""
    if not html_content or "captcha" in html_content.lower() or "api-services-support@amazon.com" in html_content:
        print("⚠️ Warning: Amazon CAPTCHA or blocking detected. Aborting this category.")
        return ""
        
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        wrappers = soup.select('div[id^="gridItemRoot"]') or soup.select('.p13n-sc-uncentered-wrapper') or soup.select('.a-list-item') or soup.select('.s-result-item')
        
        extracted_text = ""
        for i, wrap in enumerate(wrappers[:15]):
            name = wrap.select_one('.p13n-sc-truncate, .a-size-base-plus, h2, ._cDEzb_p13n-sc-css-line-clamp-3_g3dy1')
            price = wrap.select_one('.a-price-whole, .p13n-sc-price, ._cDEzb_p13n-sc-price_3mJ9Z')
            mrp = wrap.select_one('.a-text-strike')
            link = wrap.select_one('a.a-link-normal')
            
            # [IMPROVED IMAGE SCRAPING]
            image_el = wrap.select_one('img[data-a-dynamic-image], img[data-old-hires], img[src]')
            p_image = ""
            if image_el:
                if image_el.has_attr('data-a-dynamic-image'):
                    try:
                        img_data = json.loads(image_el['data-a-dynamic-image'])
                        p_image = list(img_data.keys())[-1]
                    except: pass
                
                if not p_image and image_el.has_attr('data-old-hires'):
                    p_image = image_el['data-old-hires']
                
                if not p_image and image_el.has_attr('src'):
                    src = image_el['src']
                    # Block known Amazon placeholders
                    if any(bad in src for bad in ["01jrA-8DXYL.gif", "transparent-pixel", "spacer.gif", "pixel.gif"]):
                        p_image = ""
                    else:
                        p_image = src
            
            # Filter items without real images immediately
            if not p_image:
                continue

            rating_element = wrap.select_one('i[class*="a-icon-star"] span.a-icon-alt') or wrap.select_one('span[class*="a-icon-alt"]')
            
            p_name = name.get_text(strip=True) if name else ""
            p_price = price.get_text(strip=True) if price else "Check"
            p_mrp = mrp.get_text(strip=True) if mrp else ""
            p_link = link['href'] if link and 'href' in link.attrs else "#"
            p_rating = rating_element.get_text(strip=True) if rating_element else "Not specified"
            
            item_summary = f"ITEM {i+1}: {p_name} | PRICE: {p_price} | MRP: {p_mrp} | RATING: {p_rating} | IMAGE: {p_image} | LINK: {p_link}\n"
            extracted_text += item_summary
            
        print(f"Preprocessed into structured text. Length: {len(extracted_text)}")
        return extracted_text
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return ""

def extract_products_with_ai(html_text, retry_count=0):
    """Use Gemini AI to pick the best deals from pre-structured text."""
    models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
    if retry_count == 0:
        model = random.choice(models)
    else:
        model = models[retry_count % len(models)]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Below is a list of Amazon products. Your mission is to find the absolute BEST deals for our specific niche: "Student productivity tools & Hostel life hacks under ₹500".
    
    Pick the TOP 3 products that are currently VIRAL or highly useful for students (e.g., RGB desk gadgets, hidden hostel hacks, budget tech, study organization).
    
    Return ONLY a valid JSON array of objects with keys: "name", "price", "mrp", "discount_percent", "rating", "link", "image", "hook", "pain", "fix", "loot_reason".
    
    CRITICAL RULES:
    1. BUYING MINDSET & URGENCY: Select products that look like a 'mistake price' or 'limited time loot' (e.g. 70%+ off).
    2. RATING: ONLY pick products with 4.0+ stars. Skip everything else.
    3. PRICE RANGE: ₹99 to ₹499 (Impulse zone).
    4. CONTENT FORMAT: Use aggressive Hinglish. Sound like a hostel senior sharing a secret.
       - "hook": Catchy, FOMO-driven (e.g., "Bhai ye price glitch hai ya kya? 😱")
       - "pain": Relatable student struggle (e.g., "Raat bhar padhna hai par roommates light off kar dete hain?")
       - "fix": How this solves it + why it's a steal.
       - "loot_reason": One sentence on why this is the lowest price (e.g., "Usually ₹800 ka milta hai, abhi ₹249 hai!").
    5. IMAGE: Ensure it's a high-quality main image URL.
    6. TONE VARIETY: 1 Excited, 1 Shocked, 1 Honest/Practical.
    
    DATA:
    {html_text}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_json = response.json()
        
        if "error" in res_json:
            if res_json["error"]["code"] == 429 and retry_count < 3:
                time.sleep(15)
                return extract_products_with_ai(html_text, retry_count + 1)
            return []
            
        text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
        if "```json" in text: text = text.split("```json")[1].split("```")[0].strip()
        
        products = json.loads(text)
        validated = []
        for p in products:
            try:
                # [ANTI-HALLUCINATION SHIELD]
                price_str = str(p.get('price', '0'))
                mrp_str = str(p.get('mrp', '0'))
                
                # Rule: No percent signs in price
                if '%' in price_str or '%' in mrp_str: continue 
                
                # Rule: Extract clean float values
                p_val = float(re.sub(r'[^\d.]', '', price_str))
                m_val = float(re.sub(r'[^\d.]', '', mrp_str)) if mrp_str != 'N/A' else 0
                
                # Rule: Logic check
                if m_val > 0 and p_val >= m_val: continue # Price higher than MRP? Scam.
                if p_val == 0: continue
                
                # Rule: Suspicious value check (e.g. 5 lakh percent)
                discount = str(p.get('discount_percent', '0')).replace('%', '').strip()
                d_val = float(re.search(r'\d+', discount).group()) if re.search(r'\d+', discount) else 0
                if d_val > 99 or d_val < 1: continue

                # Rule: PRICE RANGE FILTER — Only impulse-buy zone (₹99 - ₹499)
                if p_val < 99 or p_val > 499:
                    print(f"[FILTER] Skipping '{p.get('name','')}' — price ₹{int(p_val)} outside budget zone")
                    continue

                # Normalize formatting
                p['price'] = f"₹{int(p_val)}"
                if m_val > 0: p['mrp'] = f"₹{int(m_val)}"
                p['discount_percent'] = f"{int(d_val)}%"
                
                validated.append(p)
            except: continue
            
        return validated
    except Exception as e:
        print(f"Extraction error: {e}")
        return []

import urllib.parse

def clean_amazon_link(link, tag, force_domain=None):
    """Convert full Amazon links to canonical DP links, ensuring correct domain."""
    # Handle redirects (Sponsored links)
    if "url=" in link:
        try:
            parsed = urllib.parse.urlparse(link)
            queries = urllib.parse.parse_qs(parsed.query)
            if 'url' in queries:
                link = queries['url'][0]
        except: pass

    if "amzn.to" in link:
        return link
        
    asin_match = re.search(r'/(?:dp|gp/product|asin|d|product)/([A-Z0-9]{10})', link, re.IGNORECASE)
    if asin_match:
        asin = asin_match.group(1).upper()
        # Use force_domain if provided, otherwise detect from link
        domain = force_domain if force_domain else ("amazon.in" if "amazon.in" in link else "amazon.com")
        return f"https://www.{domain}/dp/{asin}?tag={tag}"
    
    # Fallback for relative links
    if not link.startswith("http"):
        domain = force_domain if force_domain else "www.amazon.in"
        link = f"https://{domain}{link if link.startswith('/') else '/' + link}"
    
    # Add tag if missing for long links only
    if "tag=" not in link and "amazon" in link:
        link += ("&" if "?" in link else "?") + f"tag={tag}"
    return link

def add_affiliate_tags(products, source_url=""):
    forced_domain = "amazon.in" if "amazon.in" in source_url else ("amazon.com" if "amazon.com" in source_url else None)
    
    for product in products:
        link = product.get('link', '')
        # Determine the tag based on the source or domain
        tag = AFFILIATE_ID_IN if AFFILIATE_ID_IN else "shashwat022-21"
            
        product['link'] = clean_amazon_link(link, tag, force_domain="amazon.in")
    return products

def update_json(new_products):
    file_path = "product.json"
    data = {"products": []}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: pass

    # Dedup by both name AND ASIN (prevents same product with different names)
    asin_pattern = re.compile(r'/dp/([A-Z0-9]{10})', re.IGNORECASE)
    existing_names = {p['name'] for p in data['products']}
    existing_asins = set()
    for p in data['products']:
        m = asin_pattern.search(p.get('link', ''))
        if m:
            existing_asins.add(m.group(1).upper())

    added_count = 0
    for product in new_products:
        # Skip placeholder / broken images
        img = product.get('image', '')
        if not img or 'PLACEHOLDER' in img or 'example.com' in img:
            print(f"[FILTER] Skipping bad image: {product.get('name','')}")
            continue

        # Skip name duplicates
        if product['name'] in existing_names:
            continue

        # Skip ASIN duplicates and validate ASIN presence
        m = asin_pattern.search(product.get('link', ''))
        asin = m.group(1).upper() if m else ''
        
        # [CRITICAL GUARD] Enforce that only links with valid ASINs are added
        if not asin:
            print(f"[FILTER] Skipping product with NO valid ASIN: {product.get('name','')}")
            continue
            
        if asin and asin in existing_asins:
            print(f"[DEDUP] Skipping ASIN duplicate: {product.get('name','')}")
            continue

        safe_name = product['name'].encode('ascii', 'replace').decode('ascii')
        print(f"Adding: {safe_name} | Tagged URL: {product['link']}")
        data['products'].insert(0, product)
        existing_names.add(product['name'])
        if asin:
            existing_asins.add(asin)
        added_count += 1

    # Keep only 100 products to avoid huge files
    data['products'] = data['products'][:100]

    with json_lock:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Added {added_count} new products.")
    return added_count > 0

def git_push_changes():
    try:
        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"Auto-update: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Pushed to Git.")
    except Exception as e:
        print(f"Git error: {e}")

def main():
    print("Starting trending product sync...")
    category_map = {
        "electronics": "Electronics",
        "kitchen": "Kitchen",
        "beauty": "Beauty",
        "computers": "Computers",
        "apparel": "Ladies Fashion",
        "shoes": "Ladies Shoes",
        "jewelry": "Ladies Jewelry",
        "hpc": "Personal Care"
    }
    
    categories = [
        "https://www.amazon.in/gp/goldbox", # Today's Deals
        "https://www.amazon.in/gp/movers-and-shakers/electronics",
        "https://www.amazon.in/gp/movers-and-shakers/kitchen",
        "https://www.amazon.in/gp/movers-and-shakers/computers",
        "https://www.amazon.in/gp/movers-and-shakers/office-products"
    ]
    
    def sync_category(url):
        slug = url.split('/')[-1]
        cat_name = category_map.get(slug, "Loot")
        print(f"[*] Syncing: {cat_name}...")
        
        try:
            html = get_amazon_trending(url)
            if html:
                extracted_text = preprocess_html(html)
                if not extracted_text:
                    print(f"[-] Skipping {cat_name}: no valid products parsed (possibly CAPTCHA).")
                    return False
                products = extract_products_with_ai(extracted_text)
                if products:
                    for p in products:
                        p['category'] = cat_name
                    products = add_affiliate_tags(products, source_url=url)
                    return update_json(products)
        except Exception as e:
            print(f"[!] Error syncing category {cat_name}: {e}")
        return False

    any_new = False
    print(f"[*] Dispatching parallel sync for {len(categories)} categories...")
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(sync_category, categories))
        any_new = any(results)

    if any_new:
        git_push_changes()
        try:
            subprocess.run([sys.executable, "bot_post.py"], check=True)
            print("[*] Triggering Auto-Blogger...")
            subprocess.run([sys.executable, "auto_blogger.py"], check=True)
        except Exception as e:
            print(f"Telegram Bot or Blogger error: {e}")
            
        # Call Facebook Bot (Handled separately with peak-hour and daily-limit logic)
        try:
            subprocess.run([sys.executable, "fb_bot_post.py"], check=True)
        except Exception as e:
            # We don't want FB errors to stop the script, just log it.
            print(f"Facebook Bot error: {e}")
    else:
        print("No new products. Picking random deals for channel activity...")
        try:
            subprocess.run([sys.executable, "bot_post.py", "--random"], check=True)
        except Exception as e:
            print(f"Telegram Bot fallback error: {e}")

        # Also call FB on random runs (Logic inside fb_bot_post.py handles limits)
        try:
            subprocess.run([sys.executable, "fb_bot_post.py"], check=True)
        except Exception as e:
            print(f"Facebook Bot fallback error: {e}")

    # MISSION 200: Trigger the Growth/Forwarder Engine after every sync
    try:
        # Skip worker accounts (forwarder) on Cloud to avoid IP bans/session issues
        if not os.getenv("GITHUB_ACTIONS"):
            print("[*] Triggering Growth Engine (auto_forwarder.py)...")
            subprocess.run([sys.executable, "auto_forwarder.py"], check=True)
        else:
            print("[*] Cloud Mode: Skipping auto_forwarder.py to keep sessions safe.")
    except Exception as e:
        print(f"Growth Engine error: {e}")

if __name__ == "__main__":
    main()
