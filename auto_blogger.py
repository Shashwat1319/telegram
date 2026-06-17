import os
import json
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "")

def get_tracked_link(target_url):
    """Wrap link with Netlify tracker for deep-linking and stats."""
    if not CLICK_TRACKER_URL:
        return target_url
    from urllib.parse import quote
    return f"{CLICK_TRACKER_URL}/go?url={quote(target_url)}"

def generate_blog_content(product):
    """Use Gemini to write a 150-200 word SEO-optimized blog post."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # Calculate discount if not present
    price_val = int(re.sub(r'[^\d]', '', str(product.get('price', '0'))))
    mrp_val = int(re.sub(r'[^\d]', '', str(product.get('mrp', '0'))))
    discount_pct = int(((mrp_val - price_val) / mrp_val) * 100) if mrp_val > price_val else 0
    
    prompt = f"""
    Write a 150-200 word SEO-optimized blog post for this product found on Amazon India.
    Tone: Friendly, catchy, and helpful (Hinglish/English mix).
    Target Audience: Budget-conscious shoppers in India.
    
    Product Details:
    Name: {product['name']}
    Price: {product['price']}
    MRP: {product['mrp']}
    Discount: {discount_pct}%
    Link: {product['link']}
    
    Requirements:
    1. Start with an exciting title.
    2. Explain why this deal is a 'Loot'.
    3. Include 3-4 bullet points on features or why to buy.
    4. MUST end with an exciting closing statement, but DO NOT include the actual URL in your text (I will append the button).
    5. Optimize for keywords like 'budget deals', 'amazon loot', 'price drop'.
    
    Format: Return ONLY the blog text. No markdown blocks like ```. Just raw text.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=30)
        res_json = r.json()
        if "candidates" not in res_json:
            print(f"[!] API Error: {res_json}")
            return None
        return res_json['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"Error generating blog: {e}")
        return None

def create_blog_file(product, content):
    """Save the blog content as an Astro-compatible markdown file."""
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', product['link'])
    asin = asin_match.group(1) if asin_match else str(hash(product['name']))[:8]
    
    # Calculate discount
    price_val = int(re.sub(r'[^\d]', '', str(product.get('price', '0'))))
    mrp_val = int(re.sub(r'[^\d]', '', str(product.get('mrp', '0'))))
    discount_pct = int(((mrp_val - price_val) / mrp_val) * 100) if mrp_val > price_val else 0
    
    blog_dir = "agency-portfolio/src/content/blog"
    if not os.path.exists(blog_dir):
        os.makedirs(blog_dir, exist_ok=True)
    
    filename = f"{asin.lower()}.md"
    file_path = os.path.join(blog_dir, filename)
    
    if os.path.exists(file_path):
        print(f"[*] Blog for {asin} already exists. Skipping.")
        return False

    date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    frontmatter = f"""---
title: "{product['name']}"
description: "Epic Deal: Save {discount_pct}% on {product['name']}! Best price alert on Amazon India."
pubDate: "{date_str}"
heroImage: "{product['image']}"
buyLink: "{get_tracked_link(product['link'])}"
---

{content}
"""
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
    
    print(f"[SUCCESS] Created blog: {filename}")
    return True

def create_deal_file(product):
    """Save the deal as an Astro-compatible markdown file for the deals collection."""
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', product['link'])
    asin = asin_match.group(1) if asin_match else str(hash(product['name']))[:8]
    
    deals_dir = "agency-portfolio/src/content/deals"
    if not os.path.exists(deals_dir):
        os.makedirs(deals_dir, exist_ok=True)
    
    filename = f"{asin.lower()}.md"
    file_path = os.path.join(deals_dir, filename)
    
    if os.path.exists(file_path):
        return False

    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Calculate discount percentage
    price_val = int(re.sub(r'[^\d]', '', str(product.get('price', '0'))))
    mrp_val = int(re.sub(r'[^\d]', '', str(product.get('mrp', '0'))))
    discount_pct = int(((mrp_val - price_val) / mrp_val) * 100) if mrp_val > price_val else 0
    
    frontmatter = f"""---
title: "{product['name']}"
description: "Save {discount_pct}% on {product['name']} - verified Amazon deal for students."
pubDate: "{date_str}"
price: "{product['price']}"
mrp: "{product['mrp']}"
discount: "{discount_pct}%"
image: "{product['image']}"
buyLink: "{get_tracked_link(product['link'])}"
category: "{product.get('category', 'General')}"
rating: "{product.get('rating', 'Not specified')}"
---

{product.get('fix', 'Great value for money deal for students!')}
"""
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
    
    print(f"[SUCCESS] Created deal page: {filename}")
    return True

def main():
    print("--- Starting Automated Content Generation ---")
    product_file = "product.json"
    if not os.path.exists(product_file):
        print("[!] No product.json found.")
        return

    with open(product_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    products = data.get("products", [])
    if not products:
        print("[!] No products to process.")
        return

    new_blogs = 0
    new_deals = 0
    
    # Process latest 5 products for deals (auto-generated pages)
    for product in products[:5]:
        print(f"[*] Creating deal page: {product['name'][:30]}...")
        if create_deal_file(product):
            new_deals += 1
    
    # Process latest 3 products for full blog posts (AI-generated)
    for product in products[:3]:
        print(f"[*] Generating blog post: {product['name'][:30]}...")
        content = generate_blog_content(product)
        if content:
            if create_blog_file(product, content):
                new_blogs += 1
    
    print(f"\n[DONE] Generated {new_blogs} blog posts + {new_deals} deal pages!")

if __name__ == "__main__":
    main()