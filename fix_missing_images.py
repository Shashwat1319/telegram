import os
import json
import requests
import re
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

PRODUCT_FILE = "product.json"

def get_amazon_image(url):
    """Fetch the product page and extract the main image URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        # Avoid tracking parameters for scraping
        clean_url = url.split('?')[0]
        response = requests.get(clean_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Multiple attempts at finding the main image
        img = soup.select_one('#landingImage') or \
              soup.select_one('#main-image') or \
              soup.select_one('#imgBlkFront') or \
              soup.select_one('img[data-old-hires]') or \
              soup.select_one('.a-dynamic-image')
        
        if img:
            if img.get('data-old-hires'): return img['data-old-hires']
            if img.get('data-a-dynamic-image'):
                # This is a JSON string of URLs, pick the largest one
                try:
                    urls = json.loads(img['data-a-dynamic-image'])
                    return max(urls.keys(), key=lambda x: int(re.search(r'(\d+)', x).group()) if re.search(r'(\d+)', x) else 0)
                except: pass
            if img.get('src'): return img['src']
            
        return None
    except Exception as e:
        print(f"Error fetching image for {url}: {e}")
        return None

def process_product(product):
    name = product.get('name', 'Unknown')
    img = product.get('image', '')
    link = product.get('link', '')
    
    # Check if image is missing or placeholder
    image_url = product.get("image", "")
    is_missing = not img or "placeholder" in img or "via.placeholder" in img or "01jrA-8DXYL.gif" in image_url or ".gif" in image_url.lower()
    
    # Also check if the URL is broken (e.g. returns 404)
    if not is_missing and image_url:
        try:
            r = requests.head(image_url, timeout=1.5)
            if r.status_code != 200:
                print(f"[*] Image returned status {r.status_code} (broken) for: {name[:40]}")
                is_missing = True
        except:
            is_missing = True
    
    if is_missing and link and "amazon" in link:
        print(f"[*] Fetching active image from Amazon page for: {name[:40]}...")
        new_img = get_amazon_image(link)
        if new_img:
            product['image'] = new_img
            print(f"[OK] Found active image: {new_img[:50]}...")
            return True
        else:
            print(f"[FAIL] Could not find active image on Amazon page for {name[:40]}")
            # Clear image so it gets filtered out of the final list
            product['image'] = ""
            return True
    return False

def main():
    if not os.path.exists(PRODUCT_FILE):
        print("Product file not found.")
        return

    with open(PRODUCT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    updated_count = 0
    
    # Run in parallel to speed up (Amazon might rate limit, but let's try small workers)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_product, products))
        updated_count = sum(1 for r in results if r)

    # Final filter for May Sprint: Price < 400 and MUST have image
    final_products = []
    for p in products:
        try:
            price_val = float(re.sub(r'[^\d.]', '', str(p.get('price', '9999'))))
            # Keep if price < 400 AND has a real image
            if price_val <= 400 and p.get('image') and "placeholder" not in p['image']:
                final_products.append(p)
        except:
            continue

    data["products"] = final_products
    
    with open(PRODUCT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\n[DONE] Updated {updated_count} images.")
    print(f"[STATS] Total products now in May Loot list: {len(final_products)}")

if __name__ == "__main__":
    main()
