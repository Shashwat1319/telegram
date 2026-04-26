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
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        wrappers = soup.select('.p13n-sc-uncentered-wrapper') or soup.select('.a-list-item') or soup.select('.s-result-item')
        
        extracted_text = ""
        for i, wrap in enumerate(wrappers[:12]):
            # Use specific selectors to guide the AI
            name = wrap.select_one('.p13n-sc-truncate, .a-size-base-plus, h2')
            price = wrap.select_one('.a-price-whole, .p13n-sc-price')
            mrp = wrap.select_one('.a-text-strike')
            link = wrap.select_one('a.a-link-normal')
            
            p_name = name.get_text(strip=True) if name else "Unknown"
            p_price = price.get_text(strip=True) if price else "Check"
            p_mrp = mrp.get_text(strip=True) if mrp else "N/A"
            p_link = link['href'] if link and 'href' in link.attrs else "#"
            
            item_summary = f"ITEM {i+1}: NAME: {p_name} | PRICE: {p_price} | MRP: {p_mrp} | LINK: {p_link}\n"
            extracted_text += item_summary
            
        print(f"Preprocessed into structured text. Length: {len(extracted_text)}")
        return extracted_text if extracted_text else html_content[:15000]
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return html_content[:15000]

def extract_products_with_ai(html_text, retry_count=0):
    """Use Gemini AI to pick the best deals from pre-structured text."""
    models = ["gemini-2.5-flash", "gemini-2.5-pro"]
    model = models[retry_count % len(models)]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Below is a list of Amazon products with prices. Pick the TOP 5 products with the BEST DISCOUNT percentage.
    Return ONLY a valid JSON array of objects with keys: "name", "price", "mrp", "discount_percent", "link", "image".
    
    CRITICAL TRUST RULES:
    1. "price" & "mrp": MUST be strings containing ONLY numbers/commas/dots (e.g. "499"). NEVER use percentage in price.
    2. "discount_percent": MUST be a valid number between 1 and 99. If math is wrong or it looks like a glitch (>99%), SKIP it.
    3. "name": Keep it slightly shortened for readability.
    
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

def clean_amazon_link(link, tag, force_domain=None):
    """Convert full Amazon links to canonical DP links, ensuring correct domain."""
    if "amzn.to" in link:
        return link
        
    asin_match = re.search(r'/(?:dp|gp/product|asin)/([A-Z0-9]{10})', link, re.IGNORECASE)
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

    existing_names = {p['name'] for p in data['products']}
    added_count = 0
    for product in new_products:
        if product['name'] not in existing_names:
            safe_name = product['name'].encode('ascii', 'replace').decode('ascii')
            print(f"Adding: {safe_name} | Tagged URL: {product['link']}")
            data['products'].insert(0, product)
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
        "https://www.amazon.in/gp/deals?discounts-widget=%257B%2522state%2522%253A%257B%2522refinementFilters%2522%253A%257B%2522pct_off%2522%253A%255B%252250-%2522%255D%257D%257D%252C%2522version%2522%253A1%257D", # 50% Off or more
        "https://www.amazon.in/gp/goldbox", # Today's Deals
        "https://www.amazon.in/gp/movers-and-shakers/electronics",
        "https://www.amazon.in/gp/movers-and-shakers/kitchen",
        "https://www.amazon.in/gp/movers-and-shakers/beauty"
    ]
    
    def sync_category(url):
        slug = url.split('/')[-1]
        cat_name = category_map.get(slug, "Loot")
        print(f"[*] Syncing: {cat_name}...")
        
        try:
            html = get_amazon_trending(url)
            if html:
                products = extract_products_with_ai(html)
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
        print("[*] Triggering Growth Engine (auto_forwarder.py)...")
        subprocess.run([sys.executable, "auto_forwarder.py"], check=True)
    except Exception as e:
        print(f"Growth Engine error: {e}")

if __name__ == "__main__":
    main()
