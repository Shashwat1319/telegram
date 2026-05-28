import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
from bs4 import BeautifulSoup
import json
import os
import re
import asyncio
import subprocess
import random
from urllib.parse import quote
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL")
CLICK_TRACKER_FUNC = f"{CLICK_TRACKER_URL}/.netlify/functions/go" if CLICK_TRACKER_URL else ""
AFFILIATE_ID_IN = os.getenv("AFFILIATE_ID_IN", "shashwat022-21")

# ---------- Short Link Helper ----------
def get_short_url(target_url):
    """Call the Netlify tracker to get a shortened, obfuscated link."""
    if not CLICK_TRACKER_URL:
        return target_url
        
    try:
        # Register new short link
        api_url = f"{CLICK_TRACKER_FUNC}?action=shorten&url={quote(target_url)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BudgetDealsBot/1.0"
        }
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            try:
                data = response.json()
                short_url = data.get("shortUrl")
                if short_url:
                    return short_url
            except Exception as json_e:
                print(f"JSON Parse Error: {json_e}")
        else:
            print(f"API Error: {response.status_code}")
            
    except Exception as e:
        print(f"Shortening request failed: {e}")
    
    # Fallback to direct tracker link
    return f"{CLICK_TRACKER_FUNC}?url={quote(target_url)}"

def get_cheap_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.text
        return None
    except:
        return None

import urllib.parse

def extract_cheap_products(html):
    if not html: return []
    
    if "captcha" in html.lower() or "api-services-support@amazon.com" in html:
        print("⚠️ Warning: Amazon CAPTCHA or blocking detected in search. Aborting.")
        return []
        
    # Preprocess
    soup = BeautifulSoup(html, 'html.parser')
    boxes = soup.select('.s-result-item')
    if not boxes or len(boxes) < 2:
        print("⚠️ Warning: No product items found in search HTML.")
        return []
        
    boxes = boxes[:25]
    cleaned = "\n".join([str(b) for b in boxes])
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    Extract up to 5 HIGH-QUALITY active products from this Amazon India search HTML.
    
    CRITICAL RULES:
    1. ONLY pick products with 4.0+ star rating.
    2. Focus on "Extreme Loot" (Branded item, 70%+ off).
    3. Price: ₹49 to ₹399.
    4. "link" MUST be extracted carefully. If it's a redirect/sponsored link, find the REAL product URL inside it (usually starts with /dp/).
    
    Return a valid JSON array of objects with keys: "name", "price", "mrp", "link", "image", "rating".
    
    HTML Data:
    {cleaned}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=30)
        res_json = r.json()
        text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except:
        return []

def format_cheap_link(link):
    # Handle redirects
    if "url=" in link:
        try:
            parsed = urllib.parse.urlparse(link)
            queries = urllib.parse.parse_qs(parsed.query)
            if 'url' in queries:
                link = queries['url'][0]
        except: pass

    asin_match = re.search(r'/(?:dp|gp/product|asin|d|product)/([A-Z0-9]{10})', link, re.IGNORECASE)
    if asin_match:
        asin = asin_match.group(1).upper()
        return f"https://www.amazon.in/dp/{asin}?tag={AFFILIATE_ID_IN}"
    return link

async def post_to_telegram(product):
    bot = Bot(token=BOT_TOKEN)
    chat_id = CHANNEL_ID if CHANNEL_ID.startswith("@") else f"@{CHANNEL_ID}"
    clean_id = chat_id.replace("@", "")
    
    link = format_cheap_link(product.get("link", ""))
    # Force a check: if no ASIN, skip
    if "dp/" not in link and "gp/" not in link: return

    tracked_link = get_short_url(link)
        
    price = str(product.get("price", "99")).replace("₹", "").replace(",", "").strip()
    mrp = str(product.get("mrp", "199")).replace("₹", "").replace(",", "").strip()
    name = str(product.get("name", "Budget Gadget")).replace('<','').replace('>','')
    image = product.get("image", "")

    try:
        p_val = float(re.sub(r'[^\d.]', '', price))
        m_val = float(re.sub(r'[^\d.]', '', mrp))
        discount = int(((m_val - p_val) / m_val) * 100) if m_val > p_val else 0
    except:
        discount = 50

    msg = (
        f"🔥 <b>{discount}% OFF - BRANDED LOOT!</b> 🔥\n\n"
        f"📦 <b>{name}</b>\n\n"
        f"❌ MRP: <strike>₹{mrp}</strike>\n"
        f"✅ <b>Loot Price:</b> <b>₹{price}</b>\n\n"
        f"🌟 <b>Rating:</b> ⭐⭐⭐⭐+ \n"
        f"🚚 <b>Delivery:</b> Free for Prime Users\n\n"
        f"👇 <b>GRAB IT NOW (Deep Link)</b> 👇\n"
        f"🛒 <a href='{tracked_link}'>Click Here to Buy</a>\n\n"
        f"👉 Join <b>@{clean_id}</b> for faster loot alerts!"
    )

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 BUY AT ₹" + price, url=tracked_link)]])
    
    try:
        if image:
            await bot.send_photo(chat_id=chat_id, photo=image, caption=msg, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=False)
        print(f"Posted: {name}")
        return True
    except Exception as e:
        print(f"Failed to post: {e}")
        return False

async def main():
    print("--- SCRAPING FRESH HIGH-VALUE DEALS ---")
    urls = [
        "https://www.amazon.in/s?k=boat+neckband&rh=p_36%3A-49900&s=review-rank",
        "https://www.amazon.in/s?k=smart+gadgets&rh=p_36%3A-29900&s=review-rank",
        "https://www.amazon.in/s?k=daily+needs+combo&rh=p_36%3A-19900&s=review-rank",
        "https://www.amazon.in/s?k=kitchen+gadgets&rh=p_36%3A-29900&s=review-rank",
        "https://www.amazon.in/s?k=wireless+earbuds&rh=p_36%3A-49900&s=review-rank"
    ]
    
    all_found = []
    for target_url in urls:
        print(f"[*] Scraping: {target_url}")
        html = get_cheap_html(target_url)
        products = extract_cheap_products(html)
        
        if products:
            for p in products:
                if len(p.get("name", "")) < 10: continue
                
                # Cleanup and Format Link
                link = format_cheap_link(p.get('link', ''))
                p['link'] = link
                
                # Validate that the link contains a real Amazon ASIN
                asin_match = re.search(r'/(?:dp|gp/product|asin|d|product)/([A-Z0-9]{10})', link, re.IGNORECASE)
                if not asin_match:
                    print(f"[-] Skipping hallucinated product (no valid ASIN): {p.get('name')}")
                    continue
                
                all_found.append(p)
                print(f"[FOUND] {p.get('name')} | Price: {p.get('price')}")
                
                # Post live
                await post_to_telegram(p)
                await asyncio.sleep(15) # Safety gap
    
    # Save/Merge to product.json for bot_post.py to use as well
    if all_found:
        existing_data = {"products": []}
        file_path = "product.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except: pass
            
        # Clean existing items' names & ASINs to dedup
        asin_pattern = re.compile(r'/dp/([A-Z0-9]{10})', re.IGNORECASE)
        existing_names = {x['name'] for x in existing_data['products']}
        existing_asins = set()
        for x in existing_data['products']:
            m = asin_pattern.search(x.get('link', ''))
            if m:
                existing_asins.add(m.group(1).upper())
                
        # Merge new ones at the beginning (newest first)
        newly_added = 0
        for p in all_found:
            # Check duplicate name
            if p['name'] in existing_names: continue
            
            # Check duplicate ASIN
            m = asin_pattern.search(p.get('link', ''))
            asin = m.group(1).upper() if m else ''
            if asin and asin in existing_asins: continue
            
            existing_data['products'].insert(0, p)
            existing_names.add(p['name'])
            if asin:
                existing_asins.add(asin)
            newly_added += 1
            
        # Keep limit at 100
        existing_data['products'] = existing_data['products'][:100]
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
            
        print(f"[SUCCESS] Merged {newly_added} fresh deals. Total products in database: {len(existing_data['products'])}")

        
if __name__ == "__main__":
    asyncio.run(main())
