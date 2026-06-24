import re
from urllib.parse import quote
from dotenv import load_dotenv
import os

load_dotenv()

CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "")


def get_price_value(price_str):
    try:
        c = re.sub(r'[^\d.]', '', str(price_str))
        return float(c) if c else 999999.0
    except:
        return 999999.0


def format_price(raw_price):
    price = str(raw_price)
    try:
        ascii_p = re.sub(r'[^\d.,\- ]', '', price).strip()
        if ascii_p:
            return f"\u20b9{ascii_p.strip().strip(',.')}"
    except:
        pass
    return price


def calc_discount(price, mrp):
    pv = get_price_value(price)
    mv = get_price_value(mrp)
    if mv > pv:
        return int(((mv - pv) / mv) * 100)
    return 0


def tracked_link(url):
    if not CLICK_TRACKER_URL:
        return url
    return f"{CLICK_TRACKER_URL}/go?url={quote(url)}"


def slugify(name):
    s = re.sub(r'[^\w\s-]', '', name.lower().replace("&", "and"))
    return re.sub(r'[-\s]+', '-', s).strip('-')[:80]


def extract_asin(link):
    if not link:
        return None
    match = re.search(r'/dp/([A-Z0-9]{10})', link, re.IGNORECASE)
    return match.group(1).lower() if match else None
