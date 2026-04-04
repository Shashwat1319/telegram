import json
import re

def clean_amazon_link(link, tag):
    """Convert any Amazon link to a clean canonical DP link with affiliate tag."""
    # Extract ASIN (10-character alphanumeric starting with B or numeric)
    asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', link)
    if asin_match:
        asin = asin_match.group(1)
        domain = "amazon.in" if "amazon.in" in link else "amazon.com"
        return f"https://www.{domain}/dp/{asin}?tag={tag}"
    return None # Return None if ASIN not found

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
