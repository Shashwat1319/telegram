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

def get_amazon_trending():
    """Scrape Amazon India Movers & Shakers (Electronics)."""
    url = "https://www.amazon.in/gp/movers-and-shakers/electronics"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch Amazon: Status {response.status_code}")
            return None
        return response.text
    except Exception as e:
        print(f"Error scraping Amazon: {e}")
        return None

def extract_products_with_ai(html_content, retry_count=0):
    """Use Gemini API via requests to extract product details with retry logic."""
    # List of models to try in order of preference
    models = ["gemini-2.0-flash", "gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
    model = models[retry_count % len(models)]
    
    # Try both v1beta and v1 endpoints
    version = "v1beta" if retry_count < 2 else "v1"
    url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Analyze the following HTML content from an Amazon India Electronics page.
    Extract the top 5 trending products.
    For each product: "name", "price", "link".
    Return results ONLY as a JSON array.
    
    HTML Content Snippet:
    {html_content[:12000]}
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
            # 429 = Quota Exceeded, 404 = Model Not Found
            if (error["code"] == 429 or error["code"] == 404) and retry_count < 3:
                wait_time = 30 if error["code"] == 429 else 1
                print(f"Issue with {model} ({error['code']}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return extract_products_with_ai(html_content, retry_count + 1)
            else:
                print(f"AI Error: {error['message']}")
                return []
            
        if "candidates" not in res_json:
            print(f"AI Error: No candidates in response.")
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

def add_affiliate_tags(products):
    """Append affiliate tags to links."""
    for product in products:
        link = product['link']
        if "amazon.in" in link:
            tag = AFFILIATE_ID_IN
        elif "amazon.com" in link:
            tag = AFFILIATE_ID_COM
        else:
            continue
        
        # Simple tag appending logic
        if "?" in link:
            product['link'] = f"{link}&tag={tag}"
        else:
            product['link'] = f"{link}?tag={tag}"
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
    added_count = 0
    for product in new_products:
        if product['name'] not in existing_names:
            data['products'].insert(0, product)  # Add new trending items to the top
            added_count += 1
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Added {added_count} new products to product.json.")
    return added_count > 0

def git_push_changes():
    """Automate git add, commit, and push."""
    try:
        subprocess.run(["git", "add", "."], check=True)
        # Use a generic commit message with timestamp
        commit_msg = f"Auto-update: Trending products added ({time.strftime('%Y-%m-%d %H:%M:%S')})"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully pushed changes to Git.")
    except Exception as e:
        print(f"Error during git push: {e}")

def main():
    print("Starting trending product sync...")
    html = get_amazon_trending()
    if html:
        products = extract_products_with_ai(html)
        if products:
            products = add_affiliate_tags(products)
            updated = update_json(products)
            if updated:
                print("New products found. Syncing with Git...")
                git_push_changes()
            else:
                print("No new products to add.")
        else:
            print("AI failed to extract products.")
    else:
        print("Failed to fetch trending data.")

if __name__ == "__main__":
    main()
