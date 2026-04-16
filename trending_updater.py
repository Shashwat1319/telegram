from bs4 import BeautifulSoup
import os
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
    """Extract only product boxes to reduce HTML size for AI."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Product boxes on Amazon India Movers & Shakers
        wrappers = soup.select('.p13n-sc-uncentered-wrapper')
        if not wrappers:
            # Fallback for different layouts
            wrappers = soup.select('.a-list-item')
            
        cleaned_html = ""
        for i, wrap in enumerate(wrappers[:10]): # Only top 10 to keep it tiny
            cleaned_html += str(wrap) + "\n"
        
        print(f"Preprocessed HTML. Reduced from {len(html_content)} to {len(cleaned_html)} characters.")
        return cleaned_html if cleaned_html else html_content[:20000]
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return html_content[:20000]

def extract_products_with_ai(html_content, retry_count=0):
    """Use Gemini API via requests to extract product details with retry logic."""
    # Using the latest April 2026 stable models
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite-preview"]
    model = models[retry_count % len(models)]
    
    # Pre-process HTML on the first try
    if retry_count == 0:
        html_content = preprocess_html(html_content)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Find the top 5 products with the HIGHEST DISCOUNT percentages from this Amazon Deals HTML snippet.
    Return ONLY a valid JSON array of objects with exact keys: "name", "price", "mrp", "discount_percent", "link", "image".
    
    CRITICAL RULES:
    1. "mrp": Find the original price before the discount.
    2. "discount_percent": Calculate or find the percentage of savings (e.g. "60%").
    3. "image": Find the high-res product image URL.
    4. "link": Extract the exact raw URL (containing /dp/ or the ASIN). MUST preserve the original domain (.in or .com).
    
    HTML Data:
    {html_content}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_json = response.json()
        
        if "error" in res_json:
            if res_json["error"]["code"] == 429 and retry_count < 5:
                print(f"Quota hit for {model}. Retrying...")
                time.sleep(20)
                return extract_products_with_ai(html_content, retry_count + 1)
            print(f"AI Error: {res_json['error']['message']}")
            return []
            
        text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
        # Clean potential markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        return json.loads(text)
    except Exception as e:
        print(f"Error with AI extraction on {model}: {e}")
        if retry_count < 2:
            return extract_products_with_ai(html_content, retry_count + 1)
        return []

def clean_amazon_link(link, tag):
    """Convert full Amazon links to canonical DP links, but leave short links alone."""
    # If it's already a short link, don't touch it!
    if "amzn.to" in link:
        return link
        
    # Improved regex for ASIN (10 characters after /dp/ or /gp/product/ or /asin/)
    asin_match = re.search(r'/(?:dp|gp/product|asin)/([A-Z0-9]{10})', link, re.IGNORECASE)
    if asin_match:
        asin = asin_match.group(1).upper()
        domain = "amazon.in" if "amazon.in" in link else "amazon.com"
        return f"https://www.{domain}/dp/{asin}?tag={tag}"
    
    # Fallback for relative links
    if not link.startswith("http"):
        domain = "www.amazon.in"
        link = f"https://{domain}{link if link.startswith('/') else '/' + link}"
    
    # Add tag if missing for long links only
    if "tag=" not in link and "amazon" in link:
        link += ("&" if "?" in link else "?") + f"tag={tag}"
    return link

def add_affiliate_tags(products):
    for product in products:
        link = product.get('link', '')
        # Determine the domain and appropriate tag
        if "amazon.in" in link:
            tag = AFFILIATE_ID_IN
        elif "amazon.com" in link:
            tag = AFFILIATE_ID_COM
        else:
            # Default to India if domain is missing
            tag = AFFILIATE_ID_IN
            
        product['link'] = clean_amazon_link(link, tag)
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
            print(f"Adding: {product['name']} | Tagged URL: {product['link']}")
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
                    products = add_affiliate_tags(products)
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
        except Exception as e:
            print(f"Telegram Bot error: {e}")
            
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
