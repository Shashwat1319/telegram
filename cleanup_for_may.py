import json
import os
import shutil
from datetime import datetime

def cleanup():
    print("--- MAY 2026 CONVERSION SPRINT: OPTION B CLEANUP ---")
    
    # 1. Product Filter (Focus on Impulse Buy < ₹400)
    PRODUCT_FILE = "product.json"
    if os.path.exists(PRODUCT_FILE):
        with open(PRODUCT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        original_count = len(data["products"])
        # Filter: Price < 400 or Discount > 70%
        filtered_products = []
        for p in data["products"]:
            try:
                price_str = str(p.get("price", "9999")).replace("₹", "").replace(",", "").strip()
                price = float(price_str)
                discount_str = str(p.get("discount_percent", "0%")).replace("%", "").strip()
                discount = int(discount_str) if discount_str.isdigit() else 0
                
                if price <= 400 or discount >= 70:
                    filtered_products.append(p)
            except:
                continue
        
        data["products"] = filtered_products
        with open(PRODUCT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[*] Filtered {original_count} products down to {len(filtered_products)} high-potential items.")

    # 2. Reset Posting History (Allow re-posting fresh for May)
    FILES_TO_DELETE = ["posted_products.json", "post_count.txt", "last_forwarded_id.txt"]
    for f in FILES_TO_DELETE:
        if os.path.exists(f):
            os.remove(f)
            print(f"[*] Deleted {f} to start fresh cycle.")

    # 3. Create fresh empty state
    with open("post_count.txt", "w") as f:
        f.write("0")
    
    print("\n[SUCCESS] Option B Complete. System is now focused on High-Conversion (Loot) items.")
    print("Ready to start member growth sprint!")

if __name__ == "__main__":
    cleanup()
