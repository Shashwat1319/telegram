import json
import re
import os

file_path = "product.json"
if not os.path.exists(file_path):
    print("product.json not found.")
    exit()

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

products = data["products"]
print(f"Before cleanup: {len(products)} products")

cleaned = []
removed_counts = {"image": 0, "price": 0, "dupe": 0}

seen_asins = set()
asin_pattern = re.compile(r'/dp/([A-Z0-9]{10})', re.IGNORECASE)

# Known placeholder images
BAD_IMAGES = [
    "01jrA-8DXYL.gif",
    "transparent-pixel",
    "PLACEHOLDER",
    "example.com",
    "no-image"
]

for p in products:
    name = p.get("name", "Unknown")
    link = p.get("link", "")
    image = p.get("image", "")
    price_str = str(p.get("price", "0"))
    
    # 1. Image Check
    is_bad_image = any(bad in image for bad in BAD_IMAGES)
    if is_bad_image or not image:
        removed_counts["image"] += 1
        continue

    # 2. Price Check (Impulse Zone: ₹99 - ₹499)
    try:
        price_num = float(re.sub(r'[^\d.]', '', price_str) or "0")
        if price_num < 99 or price_num > 999: # Allowing up to 999 for some variety, but focus is lower
            removed_counts["price"] += 1
            continue
    except:
        removed_counts["price"] += 1
        continue

    # 3. Duplicate Check
    m = asin_pattern.search(link)
    asin = m.group(1).upper() if m else name
    if asin in seen_asins:
        removed_counts["dupe"] += 1
        continue
    
    seen_asins.add(asin)
    cleaned.append(p)

data["products"] = cleaned
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"Cleanup Results:")
print(f" - Removed {removed_counts['image']} items with bad images.")
print(f" - Removed {removed_counts['price']} items outside price/logic zone.")
print(f" - Removed {removed_counts['dupe']} duplicate items.")
print(f"Final Count: {len(cleaned)} products.")
