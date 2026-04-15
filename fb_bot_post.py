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
    # Check for --force flag in command line
    if "--force" in sys.argv:
        print("[!] Force mode active. Bypassing time window checks.")
        return True

    now = datetime.datetime.now()
    
    # 1. Check Peak Hour Windows (India Buying Time)
    # Window 1: Morning (10 AM - 1 PM) | Window 2: Evening (6 PM - 10 PM)
    morning_window = (10 <= now.hour < 13)
    evening_window = (18 <= now.hour < 22)
    
    if not (morning_window or evening_window):
        print(f"[*] Skipping FB: Outside peak hours (Current: {now.strftime('%H:%M')}). Windows: 10:00-13:00, 18:00-22:00")
        return False
        
    # 2. Check Daily Limit
    # For now keeping it to 1 post per calendar day to avoid spam, but can be expanded.
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
        # 1. Hype Style
        f"{header_extra}🚨 ERROR PRICING? SYSTEM GLITCH! 🚨\n\n"
        f"🎁 {name}\n"
        f"💥 Current Price: {price} 😱\n\n"
        f"⚠️ Only active for next 5-10 minutes before Amazon fixes it!\n"
        f"👇 CLICK HERE & ADD TO CART FAST 👇\n"
        f"🛒 Buy Here: {link}\n\n"
        f"🤫 Join our SECRET Telegram for Hidden 1 Rupee Loots:\n"
        f"👉 {tg_link}\n\n"
        f"📢 Forward this to your friends! 🏃‍♂️",
    
        # 2. Verified Value Style (NEW - For Sales)
        f"{header_extra}🏆 VERIFIED TOP-QUALITY DEAL 🏆\n\n"
        f"📦 {name}\n"
        f"💰 Grab for only: {price} ✅\n\n"
        f"🌟 High-rated product with genuine savings! This is a smart buy for your home.\n"
        f"🛒 Order Now: {link}\n\n"
        f"🔥 Don't wait! Real Hidden Loots are only posted on Telegram:\n"
        f"👉 Join Now: {tg_link}",
    
        # 3. Urgency Style
        f"{header_extra}⏳ FINAL STOCK CALL! PRICE CRASH! ⏳\n\n"
        f"🌟 {name}\n"
        f"💎 Current Best Price: {price} ✨\n\n"
        f"⚠️ This deal is trending! Add to cart now to lock this price.\n"
        f"🔗 Direct Deal Link: {link}\n\n"
        f"🥇 90% of our Loots never reach Facebook. Join Telegram for VIP access:\n"
        f"👉 {tg_link}\n\n"
        f"💬 Comment 'Interested' for more such deals!"
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
