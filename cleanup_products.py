"""
One-shot cleanup: removes duplicate ASINs, broken images, and sub-₹99 products from product.json
Run once, then delete this file.
"""
import json
import re

file_path = "product.json"
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data["products"]
print(f"Before cleanup: {len(products)} products")

asin_pattern = re.compile(r'/dp/([A-Z0-9]{10})', re.IGNORECASE)
seen_asins = set()
cleaned = []

for p in products:
    name = p.get("name", "")
    link = p.get("link", "")
    image = p.get("image", "")
    price_str = str(p.get("price", "0"))

    # Filter: bad images
    if not image or "PLACEHOLDER" in image or "example.com" in image:
        print(f"  [REMOVED - bad image] {name[:60]}")
        continue

    # Filter: price below ₹99
    price_num = float(re.sub(r'[^\d.]', '', price_str) or "0")
    if price_num > 0 and price_num < 99:
        print(f"  [REMOVED - price Rs.{int(price_num)} < Rs.99] {name[:60]}")
        continue

    # Filter: ASIN duplicates
    m = asin_pattern.search(link)
    asin = m.group(1).upper() if m else None
    
    # [CRITICAL GUARD] Remove products with no valid ASIN (hallucinated / broken links)
    if not asin:
        print(f"  [REMOVED - NO VALID ASIN] {name[:60]} | Link: {link}")
        continue
        
    if asin and asin in seen_asins:
        print(f"  [REMOVED - ASIN dupe {asin}] {name[:60]}")
        continue

    if asin:
        seen_asins.add(asin)
    cleaned.append(p)

data["products"] = cleaned
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\nAfter cleanup: {len(cleaned)} products")
print(f"Removed: {len(products) - len(cleaned)} entries")
print("Done! product.json is clean.")
