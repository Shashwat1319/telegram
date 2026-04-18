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
AFFILIATE_ID_IN = os.getenv("AFFILIATE_ID_IN", "budgetdeals-21")

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

def extract_cheap_products(html):
    if not html: return []
    
    # Preprocess
    soup = BeautifulSoup(html, 'html.parser')
    boxes = soup.select('.s-result-item')[:15]
    cleaned = "\n".join([str(b) for b in boxes])
    if not cleaned: cleaned = html[:15000]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    Extract up to 3 products from this Amazon India search HTML.
    ONLY pick products where the current deal price is strictly under ₹150 (preferably under ₹99).
    If nothing is under ₹150, return an empty array [].
    
    Return a valid JSON array of objects with keys: "name", "price", "mrp", "link", "image".
    "link" MUST be the exact relative URL starting with /dp/ or /gp/.
    
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
    if "amzn.to" in link: return link
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
    if CLICK_TRACKER_URL:
        link = f"{CLICK_TRACKER_URL}/go?url={quote(link)}"
        
    price = str(product.get("price", "99"))
    mrp = str(product.get("mrp", "199"))
    name = str(product.get("name", "Budget Gadget")).replace('<','').replace('>','')
    image = product.get("image", "")

    # Ensure price symbols
    price_str = price if "₹" in price else f"₹{price}"
    mrp_str = mrp if "₹" in mrp else f"₹{mrp}"

    msg = (
        f"🤑 <b>UNDER ₹99 EXTREME LOOT!</b> 🤑\n\n"
        f"📦 <b>{name}</b>\n\n"
        f"❌ MRP: <strike>{mrp_str}</strike>\n"
        f"✅ <b>Loot Price:</b> <b>{price_str}</b>\n\n"
        f"⚠️ <i>Aise saste items jaldi out of stock hote hain! Minimum order delay na karein!</i>\n\n"
        f"👇 <b>Loot It Now</b> 👇\n"
        f"🛒 <a href='{link}'>Add to Cart & Buy</a>\n\n"
        f"👉 Join <b>@{clean_id}</b> for more 99 Rs store Loots!"
    )

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 BUY LOOT", url=link)]])
    
    try:
        if image:
            await bot.send_photo(chat_id=chat_id, photo=image, caption=msg, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=False)
        print(f"Posted Under-99 deal: {name}")
    except Exception as e:
        print(f"Failed to post: {e}")

async def main():
    print("--- Searching for Extra Cheap Items (Under ₹99) ---")
    urls = [
        "https://www.amazon.in/s?k=daily+needs&rh=p_36%3A-9900&s=price-asc-rank",
        "https://www.amazon.in/s?k=mobile+accessories&rh=p_36%3A-9900&s=price-asc-rank",
        "https://www.amazon.in/s?k=kitchen+tools&rh=p_36%3A-14900&s=price-asc-rank",
        "https://www.amazon.in/s?k=stationery&rh=p_36%3A-9900&s=price-asc-rank",
        "https://www.amazon.in/s?k=beauty+combo&rh=p_36%3A-14900&s=price-asc-rank"
    ]
    
    target_url = random.choice(urls)
    print(f"[*] Scraping Category: {target_url}")
    
    html = get_cheap_html(target_url)
    products = extract_cheap_products(html)
    
    if products:
        for p in products:
            print(f"[FOUND] {p.get('name')} | Price: {p.get('price')}")
            await post_to_telegram(p)
            await asyncio.sleep(5)
    else:
        print("[!] No deals under 150 found right now.")
        
if __name__ == "__main__":
    asyncio.run(main())
