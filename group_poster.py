import asyncio, os, json, random, logging, sys, re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, ChatGuestSendForbiddenError
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_1")
CLEAN_ID = os.getenv("CHANNEL_ID", "@smartgahr").replace("@", "")
TRACKER = os.getenv("CLICK_TRACKER_URL", "").strip()
IST = timezone(timedelta(hours=5, minutes=30))

if not API_ID or not API_HASH:
    log.error("API_ID and API_HASH environment variables are required for group poster")
    sys.exit(1)

GROUPS_FILE = "verified_promo_groups.txt"
DISCOVERED_GROUPS_FILE = "discovered_groups.txt"
POSTED_FILE = "posted_products.json"
STATE_FILE = "joined_groups_state.json"

def _content_cfg():
    from config_loader import load_config
    return load_config().get("content", {})

def _get_delay():
    cfg = _content_cfg()
    min_s = cfg.get("group_post_delay_min", 300)
    max_s = cfg.get("group_post_delay_max", 600)
    return (min_s, max_s)

def _group_window():
    return _content_cfg().get("group_window_ist", [9, 22])

def _repost_hours():
    return _content_cfg().get("group_repost_days", 7) * 24

def _group_min_gap_hours():
    try:
        return float(_content_cfg().get("group_min_gap_hours", 7))
    except (TypeError, ValueError):
        return 7.0

def _group_max_per_run():
    try:
        return max(1, int(_content_cfg().get("group_max_per_run", 25)))
    except (TypeError, ValueError):
        return 25

def _in_group_window(dt=None):
    dt = dt or datetime.now(IST)
    hour = dt.hour + dt.minute / 60
    start, end = _group_window()
    return start <= hour < end

def format_price(p):
    return f"₹{p}" if p and not str(p).startswith("₹") else str(p or "Check")

def calc_discount(price_str, mrp_str):
    try:
        p = float(re.sub(r"[^\d.]", "", str(price_str)))
        m = float(re.sub(r"[^\d.]", "", str(mrp_str)))
        if m > 0 and p < m:
            return int((1 - p / m) * 100)
    except Exception:
        pass
    return 0

def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:60]

def tracked_link(url, product=None, src=None):
    """Route clicks through the Netlify tracker with source attribution."""
    tag = os.getenv("AFFILIATE_ID_IN", "shashwat022-21")
    if not url:
        return f"https://t.me/{CLEAN_ID}"
    sep = "&" if "?" in url else "?"
    direct = f"{url}{sep}tag={tag}"
    if not TRACKER:
        return direct
    out = f"{TRACKER}/go?url={quote(direct)}"
    if product:
        pid = product.get("id") or _slug(product.get("name", "")) or "unknown"
        out += f"&product={quote(str(pid)[:60])}"
        out += f"&title={quote(str(product.get('name', ''))[:80])}"
    if src:
        out += f"&src={quote(str(src)[:40])}"
    return out


def load_groups():
    groups = []
    found = False
    for path in (GROUPS_FILE, DISCOVERED_GROUPS_FILE):
        if not os.path.exists(path):
            continue
        found = True
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    groups.append(line)
    if not found:
        log.error("%s not found", GROUPS_FILE)
        return []
    groups = list(dict.fromkeys(groups))
    # Skip chats we probed as non-writable (channels, banned, read-only)
    state_path = "joined_groups_state.json"
    if os.path.exists(state_path):
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            before = len(groups)
            groups = [
                g for g in groups
                if state.get(g, {}).get("send") in (None, "writable", "unknown")
                and state.get(g, {}).get("status") not in ("error", "not_found", "private")
            ]
            skipped = before - len(groups)
            if skipped:
                log.info("Skipped %d non-writable chats (probe state)", skipped)
        except Exception as e:
            log.warning("Could not read probe state: %s", e)
    return groups


def load_posted():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_posted(posted):
    tmp = POSTED_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(posted, f, indent=2, ensure_ascii=False)
    os.replace(tmp, POSTED_FILE)


def load_products():
    for path in ("product_home.json", "product.json"):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                products = data.get("products", [])
                if products:
                    return products
            except Exception:
                pass
    return []


def _parse_when(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _is_due(posted, key):
    """A group:product combo is due if never posted or posted >= repost window ago."""
    v = posted.get(key)
    if v is None:
        return True
    last = v if isinstance(v, str) else (v.get("last") if isinstance(v, dict) else None)
    dt = _parse_when(last)
    if dt is None:
        return True
    age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    return age_h >= _repost_hours()


def pick_due_product(group, posted):
    products = load_products()
    random.shuffle(products)
    for p in products:
        if _is_due(posted, f"{group}:{p.get('name', '')}"):
            return p
    return None


def load_latest_product():
    products = load_products()
    return random.choice(products) if products else None


def build_message(product, src=None):
    name = product.get("name", "Amazing Deal!")
    price = format_price(product.get("price", "Check"))
    mrp = product.get("mrp", "")
    drop = calc_discount(product.get("price", "0"), product.get("mrp", "0"))
    link = tracked_link(product.get("link", f"https://t.me/{CLEAN_ID}"), product=product, src=src)
    fix = product.get("fix", "Amazing value!")

    urgency_lines = [
        "⏰ Ends tonight at 11:59 PM",
        "🔥 Only few left at this price",
        "⚡ Flash deal - expires in hours",
        "📉 Lowest price in 30 days",
        "🎯 Limited stock - grab now",
    ]

    templates = [
        f"🔥 {name}\n💸 {mrp} → {price} ({drop}% OFF)\n✅ {fix}\n{random.choice(urgency_lines)}\n🛒 {link}\n\n📢 Join @{CLEAN_ID} for daily deals!",
        f"💥 PRICE DROP: {drop}% OFF\n📦 {name[:50]}\n💸 Price: {price}\n{fix}\n{random.choice(urgency_lines)}\n👉 {link}\n\n📲 @{CLEAN_ID}",
        f"⚡ DEAL ALERT!\n{name[:50]}\n💸 Just {price}\n✅ {fix}\n{random.choice(urgency_lines)}\n🛒 {link}\n\n💰 @{CLEAN_ID}",
        f"🚨 LOOT DEAL: {drop}% OFF!\n{name[:50]}\n{mrp} → {price}\n{random.choice(urgency_lines)}\n🔗 {link}\n\n📢 @{CLEAN_ID}",
    ]
    return random.choice(templates)


def mark_send_status(group, status):
    """Record actual send outcome in probe state so future runs skip failures."""
    state_path = "joined_groups_state.json"
    try:
        state = {}
        if os.path.exists(state_path):
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
        entry = state.setdefault(group, {})
        entry["send"] = status
        entry["send_at"] = datetime.now(timezone.utc).isoformat()
        tmp = state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp, state_path)
    except Exception as e:
        log.debug("Could not update send status for %s: %s", group, e)


def _load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def _group_posted_today(state, group):
    """True if the group got a post within the min-gap window (allows 2-3 rounds/day)."""
    e = state.get(group) or {}
    if e.get("send") != "writable":
        return False
    dt = _parse_when(e.get("send_at"))
    if dt is None:
        return False
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    return age < _group_min_gap_hours() * 3600


def _members_fresh(e):
    dt = _parse_when(e.get("members_at"))
    return dt is not None and (datetime.now(timezone.utc) - dt).total_seconds() < 14 * 86400


async def _sort_by_members(client, groups, state):
    """Sort groups biggest-first; cache member counts for 14 days."""
    for g in groups:
        e = state.get(g) or {}
        if isinstance(e.get("members"), int) and _members_fresh(e):
            continue
        count = None
        try:
            entity = await asyncio.wait_for(client.get_entity(g), timeout=30)
            count = getattr(entity, "participants_count", None)
            if not count:
                # Basic groups (Chat) don't carry counts on the light entity —
                # and channels may come back from cache without one either.
                cls = entity.__class__.__name__
                try:
                    if cls == "Chat":
                        from telethon.tl.functions.messages import GetFullChatRequest
                        full = await client(GetFullChatRequest(entity.id))
                    else:
                        from telethon.tl.functions.channels import GetFullChannelRequest
                        full = await client(GetFullChannelRequest(entity))
                    count = getattr(full.full_chat, "participants_count", None)
                except Exception as inner:
                    log.debug("Full fetch failed for %s: %s", g, inner)
            if isinstance(count, int) and count > 0:
                entry = state.setdefault(g, {})
                entry["members"] = count
                entry["members_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as ex:
            log.warning("Member count unavailable for %s: %s", g, ex)
    _save_state(state)

    def sort_key(g):
        m = (state.get(g) or {}).get("members")
        return (0, -m) if isinstance(m, int) else (1, 0)

    ordered = sorted(groups, key=sort_key)
    known = sum(1 for g in ordered if isinstance((state.get(g) or {}).get("members"), int))
    log.info("Posting order: %d groups (%d sized, biggest first)", len(ordered), known)
    return ordered


async def post_to_group(client, group, message, product_name, retries=2):
    for attempt in range(retries + 1):
        try:
            entity = await asyncio.wait_for(client.get_entity(group), timeout=45)
            await asyncio.wait_for(client.send_message(entity, message), timeout=45)
            log.info("Posted to %s: %s", group, product_name[:40])
            mark_send_status(group, "writable")
            return True
        except FloodWaitError as e:
            wait = e.seconds + random.randint(60, 300)
            log.warning("Flood wait %ds for %s (attempt %d/%d)", wait, group, attempt + 1, retries + 1)
            await asyncio.sleep(wait)
        except (ChatWriteForbiddenError, ChatGuestSendForbiddenError):
            log.warning("Cannot write in %s (blocked/no permission)", group)
            mark_send_status(group, "blocked")
            return False
        except Exception as e:
            log.warning("Failed to post in %s: %s", group, type(e).__name__)
            return False
    log.warning("Exhausted retries for %s", group)
    return False


async def main():
    if not _in_group_window():
        log.info("Outside group window %s IST — skipping run", _group_window())
        return
    if not SESSION_STR:
        log.error("No Telegram session found")
        return

    groups = load_groups()
    if not groups:
        log.error("No groups to post to")
        return

    state = _load_state()
    due = [g for g in groups if not _group_posted_today(state, g)]
    skipped_today = len(groups) - len(due)
    if skipped_today:
        log.info("Skipped %d groups within the %gh min-gap", skipped_today, _group_min_gap_hours())
    if not due:
        log.info("All %d writable groups posted within the last %gh", len(groups), _group_min_gap_hours())
        return
    log.info("%d/%d groups due this run", len(due), len(groups))

    posted = load_posted()

    client = TelegramClient(StringSession(SESSION_STR), int(API_ID), API_HASH, timeout=30)
    await asyncio.wait_for(client.connect(), timeout=45)
    try:
        if not await client.is_user_authorized():
            log.error("Session not authorized")
            return

        me = await client.get_me()
        log.info("Logged in as %s", me.first_name or me.phone)

        due = await _sort_by_members(client, due, state)

        cap = _group_max_per_run()
        if len(due) > cap:
            log.info("Capping run: posting to %d of %d due groups (group_max_per_run=%d)", cap, len(due), cap)
            due = due[:cap]

        posted_count = 0

        for i, group in enumerate(due):
            product = pick_due_product(group, posted)
            if not product:
                log.info("Every product still in repost window for %s — skipping", group)
                continue

            product_key = f"{group}:{product.get('name', '')}"
            msg = build_message(product, src=group.lstrip("@"))
            success = await post_to_group(client, group, msg, product.get("name", ""))
            if success:
                posted_count += 1
                posted[product_key] = datetime.now(timezone.utc).isoformat()
                save_posted(posted)

            if i < len(due) - 1:
                # Full delay only after a successful send (flood protection);
                # blocked/failed sends need just a short breather
                if success:
                    delay = random.randint(*_get_delay())
                else:
                    delay = random.randint(15, 45)
                log.info("Waiting %d seconds before next post...", delay)
                await asyncio.sleep(delay)

        log.info("Done. Posted to %d groups", posted_count)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())