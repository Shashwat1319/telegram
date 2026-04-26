import os
import json
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def generate_blog_content(product):
    """Use Gemini to write a 150-200 word SEO-optimized blog post."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Write a 150-200 word SEO-optimized blog post for this product found on Amazon India.
    Tone: Friendly, catchy, and helpful (Hinglish/English mix).
    Target Audience: Budget-conscious shoppers in India.
    
    Product Details:
    Name: {product['name']}
    Price: {product['price']}
    MRP: {product['mrp']}
    Discount: {product['discount_percent']}
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
    # Create valid filename from ASIN or slugified name
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', product['link'])
    asin = asin_match.group(1) if asin_match else str(hash(product['name']))[:8]
    
    blog_dir = "website/src/content/blog"
    if not os.path.exists(blog_dir):
        os.makedirs(blog_dir, exist_ok=True)
    
    filename = f"{asin.lower()}.md"
    file_path = os.path.join(blog_dir, filename)
    
    # Check if exists
    if os.path.exists(file_path):
        print(f"[*] Blog for {asin} already exists. Skipping.")
        return False

    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Frontmatter — buyLink stored here so the Astro layout renders the button cleanly
    frontmatter = f"""---
title: "{product['name']}"
description: "Epic Deal: Save {product['discount_percent']} on {product['name']}! Best price alert on Amazon India."
pubDate: "{date_str}"
heroImage: "{product['image']}"
buyLink: "{product['link']}"
---

{content}
"""
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
    
    print(f"[SUCCESS] Created blog: {filename}")
    return True

def main():
    print("--- Starting Automated Blog Generation ---")
    product_file = "product.json"
    if not os.path.exists(product_file):
        print("[!] No product.json found.")
        return

    with open(product_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    products = data.get("products", [])
    if not products:
        print("[!] No products to blog about.")
        return

    # Process only the latest 3 products to keep it fast
    new_blogs = 0
    for product in products[:3]:
        print(f"[*] Processing: {product['name'][:30]}...")
        content = generate_blog_content(product)
        if content:
            if create_blog_file(product, content):
                new_blogs += 1
        
    print(f"\n[DONE] Generated {new_blogs} new blog posts!")

if __name__ == "__main__":
    main()
