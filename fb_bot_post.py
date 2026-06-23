import json, random, os, requests, sys
from dotenv import load_dotenv
load_dotenv()

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_API = "v21.0"

if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
    print("[FB] Skipping: credentials missing"); exit(0)

def load_products():
    return json.load(open("product.json", encoding="utf-8"))["products"]

def generate_msg(product):
    name = product.get('name', 'Deal!')
    price = product.get('price', 'Check')
    link = product.get('link', '#')
    hook = product.get('hook', 'Great deal!')
    fix = product.get('fix', 'Amazing value.')
    tg = "https://t.me/budgetdeals_india"
    tpl = [
        f"🔥 {hook}\n\n{fix}\n\n👉 {link}\n\n📌 Join Telegram: {tg}",
        f"💥 {product.get('discount_percent', '')} OFF - {name}\n💸 {price}\n✅ {fix}\n🛒 {link}\n\n📲 More deals: {tg}",
        f"📢 Deal!\n📦 {name[:60]}\n💸 {price}\n{fix}\n👉 {link}",
    ]
    return random.choice(tpl) + "\n\n#DealsIndia #AmazonDeals #BudgetFinds"

def post_photo(product, msg):
    """Try posting as photo. Falls back to feed post if image fails."""
    url = product.get('image')
    if not url:
        return False
    r = requests.post(
        f"https://graph.facebook.com/{FB_API}/{FB_PAGE_ID}/photos",
        params={"access_token": FB_ACCESS_TOKEN, "url": url, "caption": msg, "share_to_instagram": True}
    )
    if not r.ok: return None
    j = r.json()
    return j if 'error' not in j else None

def post_feed(product, msg):
    """Post as feed update with link."""
    r = requests.post(
        f"https://graph.facebook.com/{FB_API}/{FB_PAGE_ID}/feed",
        params={"access_token": FB_ACCESS_TOKEN, "message": msg, "link": product.get('link', '#'), "share_to_instagram": True}
    )
    if not r.ok: return None
    j = r.json()
    return j if 'error' not in j else None

def post_to_facebook():
    try:
        products = load_products()
        if not products: print("[FB] No products"); return

        # Pick first product that has a link
        product = None
        for p in products:
            if p.get('link', '').strip():
                product = p
                break
        if not product:
            print("[FB] No products with links"); return

        msg = generate_msg(product)
        name = product.get('name', 'Product')[:50]

        # Try photo first, fallback to feed
        result = post_photo(product, msg)
        if result:
            print(f"[FB] POSTED (photo): {name} (ID: {result.get('id','ok')})")
            return

        feed_result = post_feed(product, msg)
        if feed_result:
            print(f"[FB] POSTED (feed): {name} (ID: {feed_result.get('id','ok')})")
        else:
            print(f"[FB] FAILED: {name}")

    except Exception as e:
        print(f"[FB] Error: {e}")

if __name__ == "__main__":
    post_to_facebook()
