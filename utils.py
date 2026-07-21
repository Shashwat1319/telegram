import re
import os
import logging
from urllib.parse import quote
from dotenv import load_dotenv
from data import load_json
from config_loader import load_config

load_dotenv()

log = logging.getLogger(__name__)

CLICK_TRACKER_URL = os.getenv("CLICK_TRACKER_URL", "")

_MD_CHARS = "\\_*[]()~`>#+-=|{}.!"

def esc_md(text):
    s = str(text)
    for c in _MD_CHARS:
        s = s.replace(c, "\\" + c)
    return s

def load_content_items(source_file=None):
    if source_file is None:
        source_file = load_config().get("content", {}).get("source_file", "content.json")
    data = load_json(source_file, default={})
    items = data.get("items", [])
    if not isinstance(items, list):
        log.warning("items is not a list, got %s", type(items).__name__)
        return []
    return [i for i in items if isinstance(i, dict) and i.get("title")]


def get_price_value(price_str):
    try:
        if price_str is None:
            return 999999.0
        c = re.sub(r'[^\d.]', '', str(price_str))
        return float(c) if c else 999999.0
    except:
        return 999999.0


def format_price(raw_price):
    price = str(raw_price)
    try:
        ascii_p = re.sub(r'[^\d.,\- ]', '', price).strip()
        if ascii_p:
            return f"\u20b9{ascii_p.strip().strip(',')}"
    except:
        pass
    return price


def tracked_url(url, product_id=None):
    if not CLICK_TRACKER_URL:
        return url
    base = f"{CLICK_TRACKER_URL}/go?url={quote(url)}"
    if product_id:
        base += f"&product={quote(product_id)}"
    return base


def extract_asin(link):
    if not link:
        return None
    match = re.search(r'/dp/([A-Z0-9]{10})', link, re.IGNORECASE)
    return match.group(1).lower() if match else None