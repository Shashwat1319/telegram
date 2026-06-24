import asyncio, os, json, random, logging
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChatWriteForbiddenError
from telethon.tl.functions.messages import SendMessageRequest
from telethon.sessions import StringSession
from dotenv import load_dotenv

from utils import get_price_value, format_price, calc_discount

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_1")
CLEAN_ID = os.getenv("CHANNEL_ID", "@budgetdeals_india").replace("@", "")

GROUPS_FILE = "verified_promo_groups.txt"
POSTED_FILE = "posted_products.json"
DELAY_BETWEEN_POSTS = (300, 600)


def load_groups():
    if not os.path.exists(GROUPS_FILE):
        log.error("%s not found", GROUPS_FILE)
        return []
    groups = []
    with open(GROUPS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                groups.append(line)
    return groups


def load_latest_product():
    if not os.path.exists("product.json"):
        return None
    try:
        data = json.load(open("product.json", encoding="utf-8"))
        products = data.get("products", [])
        posted = {}
        if os.path.exists(POSTED_FILE):
            try:
                posted = json.load(open(POSTED_FILE))
            except:
                pass

        unposted = [p for p in products if p.get("name") and p.get("name") not in posted]
        pool = unposted if unposted else products
        return random.choice(pool) if pool else None
    except:
        return None


def build_message(product):
    name = product.get("name", "Amazing Deal!")
    price = format_price(product.get("price", "Check"))
    mrp = product.get("mrp", "")
    drop = calc_discount(product.get("price", "0"), product.get("mrp", "0"))
    link = product.get("link", f"https://t.me/{CLEAN_ID}")
    fix = product.get("fix", "Amazing value!")

    templates = [
        f"🔥 {name}\n💸 {mrp} → {price} ({drop}% OFF)\n✅ {fix}\n🛒 {link}\n\n📢 Join @{CLEAN_ID} for daily deals!",
        f"💥 PRICE DROP: {drop}% OFF\n📦 {name[:50]}\n💸 Price: {price}\n{fix}\n👉 {link}\n\n📲 @{CLEAN_ID}",
        f"⚡ DEAL ALERT!\n{name[:50]}\n💸 Just {price}\n✅ {fix}\n🛒 {link}\n\n💰 @{CLEAN_ID}",
    ]
    return random.choice(templates)


async def post_to_group(client, group, message, product_name):
    try:
        entity = await client.get_entity(group)
        await client.send_message(entity, message)
        log.info("Posted to %s: %s", group, product_name[:40])
        return True
    except FloodWaitError as e:
        wait = e.seconds + random.randint(60, 300)
        log.warning("Flood wait %ds for %s", wait, group)
        await asyncio.sleep(wait)
        return False
    except ChatWriteForbiddenError:
        log.warning("Cannot write in %s (blocked/no permission)", group)
        return False
    except Exception as e:
        log.warning("Failed to post in %s: %s", group, type(e).__name__)
        return False


async def main():
    if not SESSION_STR:
        log.error("No Telegram session found")
        return

    groups = load_groups()
    if not groups:
        log.error("No groups to post to")
        return
    log.info("Loaded %d groups", len(groups))
    random.shuffle(groups)

    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log.error("Session not authorized")
        await client.disconnect()
        return

    me = await client.get_me()
    log.info("Logged in as %s", me.first_name or me.phone)

    posted_count = 0

    for i, group in enumerate(groups):
        product = load_latest_product()
        if not product:
            log.warning("No product available to post")
            break

        msg = build_message(product)
        success = await post_to_group(client, group, msg, product.get("name", ""))
        if success:
            posted_count += 1

        if i < len(groups) - 1:
            delay = random.randint(*DELAY_BETWEEN_POSTS)
            log.info("Waiting %d seconds before next post...", delay)
            await asyncio.sleep(delay)

    await client.disconnect()
    log.info("Done. Posted to %d groups", posted_count)


if __name__ == "__main__":
    asyncio.run(main())
