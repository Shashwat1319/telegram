import json
import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
import subprocess
import time

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AFFILIATE_ID_IN = os.getenv("AFFILIATE_ID_IN")
AFFILIATE_ID_COM = os.getenv("AFFILIATE_ID_COM")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

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

def extract_products_with_ai(html_content):
    """Use Gemini to extract product details from HTML."""
    prompt = f"""
    Analyze the following HTML content from an Amazon Best Sellers/Movers & Shakers page.
    Extract the top 5-10 trending products.
    For each product, I need:
    1. Product Name (Short and catchy)
    2. Current Price (with currency symbol like ₹ or $)
    3. Product Link (The direct Amazon product URL)

    Return the results ONLY as a JSON array of objects with keys: "name", "price", "link".
    Do not include any other text in your response.
    
    HTML Content Snippet (Focus on product items):
    {html_content[:10000]}  # Limit to 10k chars to avoid token limits
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
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
