import json
import random
import asyncio
import os
import re
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------- Environment variables ----------
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
# Agar inme se koi nahi hai, toh aage nahi badhenge
if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
    print("Error: FB_PAGE_ID or FB_ACCESS_TOKEN missing in .env")
    exit()

# ---------- Load products ----------
def load_products():
    with open("product.json", "r", encoding="utf-8") as f:
        return json.load(f)["products"]

# ---------- Message Templates (Facebook Format) ----------
def generate_fb_message(product):
    name = product.get('name', 'Great Deal!')
    price = product.get('price', 'Check Link')
    link = product.get('link', '#')
    
    # Facebook me HTML <b>, <i> kaam nahi karte, toh plain text + emojis use karenge
    templates = [
        f"🚨 ERROR PRICING? SYSTEM GLITCH! 🚨\n\n"
        f"🎁 {name}\n"
        f"💥 Current Price: {price} 😱\n\n"
        f"⚠️ Only active for next 5-10 minutes before Amazon fixes it!\n"
        f"👇 CLICK HERE & ADD TO CART FAST 👇\n"
        f"🛒 Buy Here: {link}\n\n"
        f"🤫 Tag your friends who love shopping! 🏃‍♂️",

        f"😱 PRICE DROP OF THE MONTH! 99% CLAIMED! 😱\n\n"
        f"📦 {name}\n"
        f"🔥 Loot Price: {price} 📉\n\n"
        f"⏳ Stock will end completely in any second! Just 3 pieces left!\n"
        f"🛒 Grab the deal: {link}\n\n"
        f"💵 Company ka loss aapka profit!\n"
        f"📢 Apne dosto ko jaldi share karo, unhe bhi lootne do!",

        f"🛑 SECRET LINK - WILL BE DELETED SOON! 🛑\n\n"
        f"🌟 {name}\n"
        f"💎 Get It Only At: {price} ✅\n\n"
        f"⚡️ Ye price wapas zindagi mein nahi aayega! Guarantee.\n"
        f"🔗 Direct Hidden Link to Buy: {link}\n\n"
        f"🚀 Follow our page to get these secret Loot daily! 🔒\n"
        f"💬 Comment 'LOOT' if you claimed this!"
    ]
    msg = random.choice(templates)
    
    # Facebook Hashtags
    seo_block = "\n\n#AmazonDeals #LootDealsIndia #FlipkartSale #BudgetShopping #Offers #Cheapest"
    return msg + seo_block

# ---------- Post to Facebook ----------
def post_to_facebook():
    products = load_products()
    
    fb_api_version = "v19.0"
    
    try:
        # Post the top 3 (newest) products found
        for i in range(min(3, len(products))):
            product = products[i]
            msg = generate_fb_message(product)
            image_url = product.get('image')
            
            if image_url:
                # If product has an image, send a Photo post
                url = f"https://graph.facebook.com/{fb_api_version}/{FB_PAGE_ID}/photos"
                payload = {
                    "url": image_url,
                    "caption": msg,
                    "access_token": FB_ACCESS_TOKEN
                }
            else:
                # If no image, send a Feed (Text + Link) post
                url = f"https://graph.facebook.com/{fb_api_version}/{FB_PAGE_ID}/feed"
                payload = {
                    "message": msg,
                    "link": product.get('link', ''), # Facebook will automatically fetch preview for this link
                    "access_token": FB_ACCESS_TOKEN
                }
            
            response = requests.post(url, data=payload)
            result = response.json()
            
            if 'error' in result:
                print(f"Failed to post {product['name']} on FB: {result['error']['message']}")
            else:
                print(f"Successfully Posted on FB: {product['name']} (Post ID: {result.get('id')})")
            
    except Exception as e:
        print(f"Error in FB posting: {e}")

if __name__ == "__main__":
    post_to_facebook()
