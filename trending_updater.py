from bs4 import BeautifulSoup
import os
import requests
import json
import re
import subprocess
import time
import random
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AFFILIATE_ID_IN = os.getenv("AFFILIATE_ID_IN")
AFFILIATE_ID_COM = os.getenv("AFFILIATE_ID_COM")

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
    Extract the top 5 trending products from this Amazon Movers & Shakers HTML snippet.
    Return ONLY a valid JSON array of objects with exact keys: "name", "price", "link", "image".
    
    CRITICAL RULES:
    1. "image": Find the high-res product image URL. If not found, return an empty string "".
    2. "link": You MUST extract the exact raw URL (containing /dp/ or the ASIN). NEVER EVER generate or return "amzn.to" shortlinks.
    
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
        link = product['link']
        tag = AFFILIATE_ID_IN if "amazon.in" in link or ("amazon.in" not in link and "amazon.com" not in link) else AFFILIATE_ID_COM
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
        "https://www.amazon.in/gp/movers-and-shakers/electronics",
        "https://www.amazon.in/gp/movers-and-shakers/kitchen",
        "https://www.amazon.in/gp/movers-and-shakers/beauty",
        "https://www.amazon.in/gp/movers-and-shakers/computers",
        "https://www.amazon.in/gp/movers-and-shakers/apparel",
        "https://www.amazon.in/gp/movers-and-shakers/shoes",
        "https://www.amazon.in/gp/movers-and-shakers/jewelry",
        "https://www.amazon.in/gp/movers-and-shakers/hpc"
    ]
    
    any_new = False
    for url in categories:
        slug = url.split('/')[-1]
        cat_name = category_map.get(slug, "Loot")
        print(f"Syncing: {cat_name}...")
        
        html = get_amazon_trending(url)
        if html:
            products = extract_products_with_ai(html)
            if products:
                # Tag each product with its category
                for p in products:
                    p['category'] = cat_name
                products = add_affiliate_tags(products)
                if update_json(products):
                    any_new = True
        time.sleep(random.randint(5, 10))

    if any_new:
        git_push_changes()
        try:
            subprocess.run([sys.executable, "bot_post.py"], check=True)
        except Exception as e:
            print(f"Telegram Bot error: {e}")
    else:
        print("No new products. Picking random deals for channel activity...")
        try:
            subprocess.run([sys.executable, "bot_post.py", "--random"], check=True)
        except Exception as e:
            print(f"Telegram Bot fallback error: {e}")

if __name__ == "__main__":
    main()
