import json
import random
import asyncio
import os
import re
import requests
import time
import sys
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------- Environment variables ----------
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_POST_STATE_FILE = "last_fb_post.txt"

# Agar inme se koi nahi hai, toh aage nahi badhenge
if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
    print("Error: FB_PAGE_ID or FB_ACCESS_TOKEN missing in .env")
    exit()

# ---------- Daily & Peak Hour Logic ----------
def can_post_to_fb():
    now = datetime.datetime.now()
    
    # 1. Check Peak Hour (6 PM - 10 PM / 18:00 - 22:00)
    # Note: User requested "jab log jayada hote h", 6-10 PM is ideal for India.
    if not (18 <= now.hour < 22):
        print(f"[*] Skipping FB: Outside peak hours (Current: {now.strftime('%H:%M')}). Window: 18:00-22:00")
        return False
        
    # 2. Check Daily Limit
    today = now.strftime("%Y-%m-%d")
    if os.path.exists(FB_POST_STATE_FILE):
        try:
            with open(FB_POST_STATE_FILE, "r") as f:
                last_date = f.read().strip()
                if last_date == today:
                    print(f"[*] Skipping FB: Already posted today ({today}).")
                    return False
        except: pass
    
    return True

def mark_fb_posted():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(FB_POST_STATE_FILE, "w") as f:
        f.write(today)

# ---------- Load products ----------
def load_products():
    with open("product.json", "r", encoding="utf-8") as f:
        return json.load(f)["products"]

# ---------- Message Templates (Facebook Format) ----------
def generate_fb_message(product):
    name = product.get('name', 'Great Deal!')
    price = product.get('price', 'Check Link')
    link = product.get('link', '#')
    category = product.get('category', 'Loot')
    
    # Identify Ladies Categories
    ladies_cats = ["Ladies Fashion", "Ladies Shoes", "Ladies Jewelry", "Beauty", "Personal Care"]
    is_ladies = any(c in category for c in ladies_cats)
    
    header_extra = ""
    if is_ladies:
        header_extra = "💃 LADIES SPECIAL LOOT 💃\n✨ Special deal for our lady followers! 👜💄\n\n"

    # Facebook me HTML <b>, <i> kaam nahi karte, toh plain text + emojis use karenge
    tg_link = "https://t.me/budgetdeals_india"
    
    templates = [
        f"{header_extra}🚨 ERROR PRICING? SYSTEM GLITCH! 🚨\n\n"
        f"🎁 {name}\n"
        f"💥 Current Price: {price} 😱\n\n"
        f"⚠️ Only active for next 5-10 minutes before Amazon fixes it!\n"
        f"👇 CLICK HERE & ADD TO CART FAST 👇\n"
        f"🛒 Buy Here: {link}\n\n"
        f"🤫 Join our SECRET Telegram for more Glitch Deals:\n"
        f"👉 {tg_link}\n\n"
        f"📢 Forward this to your friends! 🏃‍♂️",
    
        f"{header_extra}😱 PRICE DROP OF THE MONTH! 99% CLAIMED! 😱\n\n"
        f"📦 {name}\n"
        f"🔥 Loot Price: {price} 📉\n\n"
        f"⏳ Stock will end completely in any second! Just 3 pieces left!\n"
        f"🛒 Grab the deal: {link}\n\n"
        f"💵 Company ka loss aapka profit!\n"
        f"🚀 Join Telegram for Instant Alerts:\n"
        f"👉 {tg_link}",
    
        f"{header_extra}🛑 SECRET LINK - WILL BE DELETED SOON! 🛑\n\n"
        f"🌟 {name}\n"
        f"💎 Get It Only At: {price} ✅\n\n"
        f"⚡️ Ye price wapas zindagi mein nahi aayega! Guarantee.\n"
        f"🔗 Direct Hidden Link to Buy: {link}\n\n"
        f"🤫 Real Loot deals are first posted on Telegram:\n"
        f"🔥 Join Now: {tg_link}\n\n"
        f"💬 Comment 'LOOT' if you claimed this!"
    ]
    msg = random.choice(templates)
    
    # Facebook Hashtags
    seo_block = "\n\n#AmazonDeals #LootDealsIndia #FlipkartSale #BudgetShopping #Offers #Cheapest"
    return msg + seo_block

# ---------- Post to Facebook ----------
def post_to_facebook():
    if not can_post_to_fb():
        return

    products = load_products()
    fb_api_version = "v19.0"
    
    try:
        # Post only ONE (the newest) product found for Facebook (as requested)
        if not products:
            print("No products found to post on FB.")
            return

        product = products[0]
        msg = generate_fb_message(product)
        image_url = product.get('image')
        product_name = product.get('name', 'Product').encode('ascii', 'ignore').decode('ascii')
        
        # Use Page Access Token from .env
        params = {
            "access_token": FB_ACCESS_TOKEN
        }
        
        if image_url:
            # FB Photos API use 'caption' for photo posts
            url = f"https://graph.facebook.com/{fb_api_version}/{FB_PAGE_ID}/photos"
            payload = {
                "url": image_url,
                "caption": msg
            }
        else:
            # FB Feed API use 'message'
            url = f"https://graph.facebook.com/{fb_api_version}/{FB_PAGE_ID}/feed"
            payload = {
                "message": msg,
                "link": product.get('link', '')
            }
        
        # Merge params and payload safely
        response = requests.post(url, params=params, data=payload)
        result = response.json()
        
        if 'error' in result:
            error_msg = result['error'].get('message', 'Unknown Error')
            error_code = result['error'].get('code', 'N/A')
            print(f"Failed to post {product_name} on FB: [{error_code}] {error_msg}")
        else:
            print(f"Successfully Posted on FB: {product_name} (Post ID: {result.get('id')})")
            mark_fb_posted() # Update state to prevent double-posting today
            
    except Exception as e:
        print(f"Error in FB posting: {str(e).encode('ascii', 'ignore').decode('ascii')}")

if __name__ == "__main__":
    post_to_facebook()
