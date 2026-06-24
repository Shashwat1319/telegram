import json, random, os, requests, sys, logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_API = "v21.0"

if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
    log.warning("Skipping: Facebook credentials missing")
    exit(0)

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
    """Post as feed update with optional link."""
    link = product.get('link', '').strip()
    params = {"access_token": FB_ACCESS_TOKEN, "message": msg, "share_to_instagram": True}
    if link: params["link"] = link
    r = requests.post(f"https://graph.facebook.com/{FB_API}/{FB_PAGE_ID}/feed", params=params)
    if not r.ok: return None
    j = r.json()
    return j if 'error' not in j else None

def post_to_facebook():
    try:
        products = load_products()
        if not products:
            log.warning("No products to post to Facebook")
            return

        product = products[0]
        msg = generate_msg(product)
        name = product.get('name', 'Product')[:50]

        result = post_photo(product, msg)
        if result:
            log.info("POSTED (photo): %s (ID: %s)", name, result.get('id', 'ok'))
            return

        feed_result = post_feed(product, msg)
        if feed_result:
            log.info("POSTED (feed): %s (ID: %s)", name, feed_result.get('id', 'ok'))
        else:
            log.error("FAILED to post: %s", name)

    except Exception as e:
        log.error("Facebook post error: %s", e)

if __name__ == "__main__":
    post_to_facebook()
