import json
import re

def clean_amazon_link(link, tag):
    """Convert any Amazon link to a clean canonical DP link with affiliate tag."""
    # Attempt to extract ASIN from various Amazon URL patterns
    asin_match = re.search(
        r'/(?:dp|gp/product|gp/aw/d|dp|gp/aw)/[^\"]*?([A-Z0-9]{10})',
        link,
        re.IGNORECASE,
    )
    if not asin_match:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(link).query)
        asin = qs.get("ASIN", [None])[0] or qs.get("asin", [None])[0]
        if asin and re.fullmatch(r"[A-Z0-9]{10}", asin, re.IGNORECASE):
            asin_match = type("obj", (object,), {"group": lambda _: asin.upper()})()
    if asin_match:
        asin = asin_match.group(1).upper()
        domain = "amazon.in" if "amazon.in" in link else "amazon.com"
        return f"https://www.{domain}/dp/{asin}?tag={tag}"
    return None

def cleanup():
    file_path = "product.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    new_products = []
    removed_count = 0
    tag_in = "shashwat022-21"
    tag_com = "shashwat01-20"
    
    for product in data['products']:
        link = product['link']
        tag = tag_in if "amazon.in" in link else tag_com
        cleaned_link = clean_amazon_link(link, tag)
        
        if cleaned_link:
            product['link'] = cleaned_link
            new_products.append(product)
        else:
            print(f"Removing invalid link: {product['name']}")
            removed_count += 1
            
    data['products'] = new_products
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Cleanup complete. Removed {removed_count} invalid products.")

if __name__ == "__main__":
    cleanup()
