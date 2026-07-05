import asyncio, os, json, re, random, logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, ChatWriteForbiddenError
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
CHANNEL = os.getenv('CHANNEL_ID', '@budgetdeals_india')

SESSIONS = [
    os.getenv('TELEGRAM_SESSION_1'),
    os.getenv('TELEGRAM_SESSION_2'),
    os.getenv('TELEGRAM_SESSION_3'),
]
ACCOUNT_NAMES = ['account_1', 'account_2', 'account_3']

LEADS_FILE = 'scraped_leads.txt'
HISTORY_FILE = 'promo_history.json'

# Conservative limits to avoid flood waits
MAX_MSGS_PER_ACCOUNT_PER_DAY = 30
DELAY_BETWEEN_MSGS = (180, 300)  # 3-5 minutes between messages
DELAY_BETWEEN_ACCOUNTS = (600, 1200)  # 10-20 minutes between accounts
INITIAL_DELAY = (30, 120)  # Initial delay before first account starts

MESSAGES = [
    "Hey! 👋\n\nI run @budgetdeals_india — we post handpicked Amazon India deals with crazy discounts (up to 70% off) on electronics, home, fashion & more.\n\nJoin & never overpay again: https://t.me/budgetdeals_india",
    "Hi there! 😊\n\nFound some absolutely insane deals on Amazon lately — thought you'd wanna know.\n\nI share them all here: @budgetdeals_india\n\nEverything from gadgets to daily essentials at the lowest prices 🔥",
    "Hey! 👋\n\nIf you shop on Amazon, you'll love @budgetdeals_india. We find the best price drops & share them instantly.\n\nLatest example: products at 50-70% off. Join and save big! 🚀",
    "Hello! 😊\n\nWant to know about the best Amazon deals BEFORE they go out of stock?\n\n@budgetdeals_india posts verified deals daily with direct buy links. Check it out! 💰",
]


def load_leads():
    if not os.path.exists(LEADS_FILE):
        log.error("%s not found!", LEADS_FILE)
        return [], []
    raw = open(LEADS_FILE, encoding='utf-8').read().strip().split('\n')
    usernames, phones = [], []
    for line in raw:
        line = line.strip()
        if not line:
            continue
        if line.startswith('@'):
            usernames.append(line[1:])
        elif line.startswith('+'):
            phones.append(line)
    return usernames, phones


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            return json.load(open(HISTORY_FILE, encoding='utf-8'))
        except:
            return {}
    return {}


def save_history(data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def filter_new(usernames, phones, history):
    already = set()
    for k in history:
        already.add(k.lower())
        if k.startswith('@'):
            already.add(k[1:].lower())
    new_users = [u for u in usernames if u.lower() not in already and '@' + u.lower() not in already]
    new_phones = [p for p in phones if p.lower() not in already]
    return new_users, new_phones


def count_today_sends(history, account_name):
    """Count messages sent by this account today."""
    today = datetime.now().date().isoformat()
    count = 0
    for data in history.values():
        if isinstance(data, dict) and data.get('account') == account_name:
            if data.get('time', '').startswith(today):
                count += 1
    return count


async def resolve_entity(client, identifier):
    try:
        if identifier.startswith('+'):
            return await client.get_input_entity(identifier)
        else:
            result = await client(ResolveUsernameRequest(identifier))
            if result and result.peer:
                return result.peer
    except:
        pass
    return None


async def send_promo(client, entity, message, contact_id, account_name, max_retries=3):
    """Send with exponential backoff on flood wait."""
    for attempt in range(max_retries):
        try:
            await client.send_message(entity, message)
            return True
        except FloodWaitError as e:
            wait = e.seconds + random.randint(120, 300)  # 2-5 min extra
            log.warning("[%s] Flood wait %ds for %s (attempt %d/%d)",
                        account_name, wait, contact_id, attempt + 1, max_retries)
            await asyncio.sleep(wait)
        except UserPrivacyRestrictedError:
            log.warning("[%s] Privacy restricted: %s", account_name, contact_id)
            return False
        except ChatWriteForbiddenError:
            log.warning("[%s] Blocked by: %s", account_name, contact_id)
            return False
        except Exception as e:
            log.error("[%s] Failed send to %s: %s", account_name, contact_id, type(e).__name__)
            return False
    log.error("[%s] Max retries reached for %s", account_name, contact_id)
    return False


async def process_account(account_idx, usernames, phones, history):
    session_str = SESSIONS[account_idx]
    if not session_str:
        log.warning("Account %d: no session", account_idx + 1)
        return 0

    account_name = ACCOUNT_NAMES[account_idx]

    # Check daily limit
    sent_today = count_today_sends(history, account_name)
    if sent_today >= MAX_MSGS_PER_ACCOUNT_PER_DAY:
        log.info("[%s] Daily limit reached (%d/%d), skipping",
                 account_name, sent_today, MAX_MSGS_PER_ACCOUNT_PER_DAY)
        return 0

    remaining_today = MAX_MSGS_PER_ACCOUNT_PER_DAY - sent_today

    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log.error("Account %d not authorized", account_idx + 1)
        await client.disconnect()
        return 0

    me = await client.get_me()
    log.info("[%s] Logged in as %s", account_name, me.first_name or me.phone)

    sent_count = 0
    targets = []

    split = len(ACCOUNT_NAMES)
    my_users = usernames[account_idx::split]
    my_phones = phones[account_idx::split]

    for u in my_users:
        if f'@{u.lower()}' not in history and u.lower() not in {k.lower().lstrip("@") for k in history}:
            targets.append(('user', u))

    for p in my_phones:
        if p.lower() not in history:
            targets.append(('phone', p))

    random.shuffle(targets)
    total = len(targets)
    log.info("[%s] %d new leads available, can send %d today", account_name, total, remaining_today)

    for i, (ttype, tid) in enumerate(targets):
        if sent_count >= remaining_today:
            log.info("[%s] Reached daily limit (%d)", account_name, remaining_today)
            break

        entity = await resolve_entity(client, tid)
        if not entity:
            entity_str = f"@{tid}" if ttype == 'user' else tid
            history_key = f'@{tid}' if ttype == 'user' else tid
            history[history_key] = {'time': datetime.now().isoformat(), 'account': account_name}
            log.info("[SKIP] %s: could not resolve", entity_str)
            continue

        msg = random.choice(MESSAGES)
        success = await send_promo(client, entity, msg, tid, account_name)

        history_key = f'@{tid}' if ttype == 'user' else tid
        if success:
            history[history_key] = {'time': datetime.now().isoformat(), 'account': account_name}
            sent_count += 1
            log.info("[%s] Sent %d/%d to %s", account_name, sent_count, remaining_today, tid)
        else:
            history[history_key] = {'time': datetime.now().isoformat(), 'account': account_name, 'failed': True}

        if i < total - 1 and sent_count < remaining_today:
            delay = random.randint(*DELAY_BETWEEN_MSGS)
            log.info("[%s] Waiting %ds before next message...", account_name, delay)
            await asyncio.sleep(delay)

        if sent_count % 5 == 0 and sent_count > 0:
            save_history(history)

    save_history(history)
    await client.disconnect()
    log.info("[%s] Done. Sent %d messages today.", account_name, sent_count)
    return sent_count


async def main():
    log.info("=== BUDGET DEALS PROMO SENDER ===")
    usernames, phones = load_leads()
    log.info("Total leads: %d usernames, %d phones", len(usernames), len(phones))

    history = load_history()
    new_users, new_phones = filter_new(usernames, phones, history)
    log.info("New leads: %d usernames, %d phones", len(new_users), len(new_phones))

    if not new_users and not new_phones:
        log.info("All leads already contacted!")
        return

    # Process accounts SEQUENTIALLY to avoid parallel flood waits
    total_sent = 0
    for i in range(3):
        if i > 0:
            inter_delay = random.randint(*DELAY_BETWEEN_ACCOUNTS)
            log.info("Waiting %ds before starting account %d...", inter_delay, i + 1)
            await asyncio.sleep(inter_delay)

        result = await process_account(i, new_users, new_phones, history)
        total_sent += result

        # Reload history for next account
        history = load_history()

    log.info("COMPLETE: %d messages sent across 3 accounts", total_sent)


if __name__ == '__main__':
    asyncio.run(main())