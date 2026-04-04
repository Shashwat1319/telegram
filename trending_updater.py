from bs4 import BeautifulSoup
import os
import requests
import json
from dotenv import load_dotenv
import subprocess
import time

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AFFILIATE_ID_IN = os.getenv("AFFILIATE_ID_IN")
AFFILIATE_ID_COM = os.getenv("AFFILIATE_ID_COM")

# Gemini Configuration handled via direct requests in extract_products_with_ai

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

def extract_products_with_ai(html_content, retry_count=0):
    """Use Gemini API via requests to extract product details with retry logic."""
    # Modern 2026 model lineup
    models = [
        "gemini-2.5-flash", 
        "gemini-2.5-flash-lite", 
        "gemini-2.5-pro", 
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]
    model = models[retry_count % len(models)]
    
    # Cycle through API versions
    versions = ["v1beta", "v1"]
    version = versions[(retry_count // len(models)) % len(versions)]
    
    url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Analyze the following HTML content from an Amazon India Movers & Shakers page.
    Extract the top 5 trending products.
    For each product: "name", "price", "link", "image" (The high-res product image URL).
    Return results ONLY as a JSON array.
    
    HTML Content Snippet:
    {html_content[:15000]}
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        res_json = response.json()
        
        if "error" in res_json:
            error = res_json["error"]
            if (error["code"] == 429 or error["code"] == 404 or error["code"] == 400) and retry_count < len(models) * 2:
                wait_time = 30 if error["code"] == 429 else 1
                if error["code"] == 429:
                    print(f"Quota hit for {model}. Waiting {wait_time}s...")
                else:
                    print(f"Skipping {model} ({error['code']}). Trying next...")
                time.sleep(wait_time)
                return extract_products_with_ai(html_content, retry_count + 1)
            else:
                print(f"AI Error ({model}): {error['message']}")
                return []
            
        if "candidates" not in res_json:
            print(f"AI Error ({model}): Response structure unknown.")
            return []
            
        text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Robust JSON extraction from markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        return json.loads(text)
    except Exception as e:
        print(f"Error with AI extraction: {e}")
        return []

def clean_amazon_link(link, tag):
    """Convert any Amazon link to a clean canonical DP link with affiliate tag."""
    import re
    # Extract ASIN (10-character alphanumeric starting with B or numeric)
    asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', link)
    if asin_match:
        asin = asin_match.group(1)
        domain = "amazon.in" if "amazon.in" in link else "amazon.com"
        return f"https://www.{domain}/dp/{asin}?tag={tag}"
    
    # If ASIN extraction fails, at least ensure it's a full URL
    if not link.startswith("http"):
        domain = "www.amazon.in" # Default
        link = f"https://{domain}{link if link.startswith('/') else '/' + link}"
    
    # Add tag if missing
    if "tag=" not in link:
        link += ("&" if "?" in link else "?") + f"tag={tag}"
    return link

def add_affiliate_tags(products):
    """Clean links and append affiliate tags."""
    for product in products:
        link = product['link']
        tag = AFFILIATE_ID_IN if "amazon.in" in link or "amazon.in" not in link and "amazon.com" not in link else AFFILIATE_ID_COM
        product['link'] = clean_amazon_link(link, tag)
    return products

def update_json(new_products):
    """Update product.json if products don't already exist."""
    file_path = "product.json"
    if not os.path.exists(file_path):
        data = {"products": []}
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    existing_names = {p['name'] for p in data['products']}
    added_products = []
    for product in new_products:
        if product['name'] not in existing_names:
            data['products'].insert(0, product)  # Add new trending items to the top
            added_products.append(product)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Added {len(added_products)} new products to product.json.")
    return len(added_products) > 0

def git_push_changes():
    """Automate git add, commit, and push."""
    try:
        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"Auto-update: Trending products added ({time.strftime('%Y-%m-%d %H:%M:%S')})"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully pushed changes to Git.")
    except Exception as e:
        print(f"Error during git push: {e}")

def main():
    print("Starting trending product sync...")
    
    categories = [
        "https://www.amazon.in/gp/movers-and-shakers/electronics",
        "https://www.amazon.in/gp/movers-and-shakers/kitchen",
        "https://www.amazon.in/gp/movers-and-shakers/beauty",
        "https://www.amazon.in/gp/movers-and-shakers/computers"
    ]
    
    any_new = False
    for url in categories:
        cat_name = url.split('/')[-1]
        print(f"Syncing category: {cat_name}...")
        html = get_amazon_trending(url)
        if html:
            products = extract_products_with_ai(html)
            if products:
                products = add_affiliate_tags(products)
                if update_json(products):
                    any_new = True
            else:
                print(f"AI failed for {cat_name}")
        
        # Random delay to avoid detection
        delay = random.randint(5, 12)
        print(f"Waiting {delay}s before next category...")
        time.sleep(delay)

    if any_new:
        print("New products found. Syncing with Git and Telegram...")
        git_push_changes()
        print("Triggering Telegram bot...")
        try:
            import sys
            subprocess.run([sys.executable, "bot_post.py"], check=True)
        except Exception as e:
            print(f"Error triggering bot: {e}")
    else:
        print("No new products found across all categories.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
