import re

def clean_amazon_link(link, tag):
    """Convert full Amazon links to canonical DP links, but leave short links alone."""
    # If it's already a short link, don't touch it!
    if "amzn.to" in link:
        return link
        
    # Improved regex for ASIN (10 characters after /dp/ or /gp/product/ or /asin/)
    asin_match = re.search(r'/(?:dp|gp/product|asin)/([A-Z0-9]{10})', link, re.IGNORECASE)
    if asin_match:
        asin = asin_match.group(1).upper()
        domain = "amazon.in" if "amazon.in" in link else "amazon.com"
        return f"https://www.{domain}/dp/{asin}?tag={tag}"
    
    # Fallback for relative links
    if not link.startswith("http"):
        domain = "www.amazon.in"
        link = f"https://{domain}{link if link.startswith('/') else '/' + link}"
    
    # Add tag if missing for long links only
    if "tag=" not in link and "amazon" in link:
        link += ("&" if "?" in link else "?") + f"tag={tag}"
    return link

# Test Cases
test_cases = [
    ("https://amzn.to/4pYjwMT", "shashwat-21", "SHOULD BE UNTOUCHED"),
    ("https://www.amazon.in/boAt-Airdopes-141-Bluetooth-Earbuds/dp/B09JV7S9X1/ref=ms_sh_e_0", "shashwat-21", "SHOULD BE CANONICAL"),
    ("https://www.amazon.com/gp/product/B0CZPT6T7S", "shashwat-21", "SHOULD BE CANONICAL COM"),
    ("/dp/B0CYB1K1X1", "shashwat-21", "SHOULD BE FULL URL"),
    ("https://www.amazon.in/products?asin=B0CYB1K1X1", "shashwat-21", "SHOULD ADD TAG IF MISSING")
]

print("--- LINK VALIDATION TEST ---")
for original, tag, desc in test_cases:
    cleaned = clean_amazon_link(original, tag)
    print(f"DESC: {desc}")
    print(f"Original: {original}")
    print(f"Cleaned:  {cleaned}")
    print("-" * 30)
