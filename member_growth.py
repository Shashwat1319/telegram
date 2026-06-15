import asyncio, os, random
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load env vars
load_dotenv()
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION = os.getenv('TELEGRAM_SESSION_2')  # worker with admin rights on the channel
CHANNEL_ID = os.getenv('CHANNEL_ID').replace('@', '')

# Optional: list of your own groups to forward top deals (comma‑separated)
GROWTH_TARGET_GROUPS = [g.strip() for g in os.getenv('GROWTH_TARGET_GROUPS', '').split(',') if g]

# Import helpers from existing code
from bot_post import generate_viral_message  # re‑use the viral template function
from referral_manager import generate_referral_link

from telethon.tl.functions.messages import ExportChatInviteRequest
import json

async def _get_invite_link(client: TelegramClient) -> str:
    """Export a permanent invite link for the main channel."""
    try:
        result = await client(ExportChatInviteRequest(peer=CHANNEL_ID))
        return result.link
    except Exception as e:
        print(f"Failed to get invite link: {e}")
        return f"https://t.me/{CHANNEL_ID}"

async def _post_viral_comments(client: TelegramClient, invite_link: str):
    """Send a short promotional comment (the viral template) to each big channel.
    The comment includes the invite link so readers can join.
    """
    from traffic_hijacker import TARGET_CHANNELS
    for ch in TARGET_CHANNELS:
        msg = generate_viral_message().replace('{share_url}', invite_link)
        try:
            await client.send_message(ch, msg)
            print(f"[PROMO] Commented in {ch}")
        except Exception as e:
            print(f"[PROMO‑ERR] {ch}: {e}")
        await asyncio.sleep(random.randint(2, 5))

async def _dm_random_members(client: TelegramClient, invite_link: str):
    """Pick a handful of recent channel participants and DM them the invite.
    Also generate a personal referral link for each.
    """
    participants = await client.get_participants(CHANNEL_ID, limit=200)
    random.shuffle(participants)
    for user in participants[:10]:
        try:
            # Generate referral link natively with Telethon to avoid asyncio.run() crash
            result = await client(ExportChatInviteRequest(peer=CHANNEL_ID, usage_limit=0))
            personal_link = result.link
            
            # Save it to referrals.json manually
            referral_file = 'referrals.json'
            if os.path.exists(referral_file):
                with open(referral_file, 'r', encoding='utf-8') as f:
                    referrals = json.load(f)
            else:
                referrals = {}
            referrals[personal_link] = {
                'creator': user.id,
                'created_at': datetime.utcnow().isoformat(),
                'joined': []
            }
            with open(referral_file, 'w', encoding='utf-8') as f:
                json.dump(referrals, f, ensure_ascii=False, indent=2)

            msg = (
                f"Hey {user.first_name or ''}! 🙏 Join our deals channel for exclusive loot.\n"
                f"Your personal invite (you get credit for any friends you bring):\n{personal_link}\n"
                f"Or use the generic link: {invite_link}\n"
                "Thanks!"
            )
            await client.send_message(user.id, msg)
            print(f"[DM] Sent invite to {user.id}")
        except Exception as e:
            print(f"[DM‑ERR] {user.id}: {e}")
        await asyncio.sleep(random.randint(2, 5))

async def run():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()
    try:
        invite_link = await _get_invite_link(client)
        await _post_viral_comments(client, invite_link)
        await _dm_random_members(client, invite_link)
        # Optionally forward top‑deal to your own groups (if any)
        if GROWTH_TARGET_GROUPS:
            from bot_post import generate_message  # re‑use existing deal builder
            # Get a fresh deal (same logic as bot_post uses)
            # Here we simply reuse the first product in product.json for demo
            import json
            with open('product.json', encoding='utf-8') as f:
                products = json.load(f)
            if products:
                deal_msg = generate_message(products[0])
                for grp in GROWTH_TARGET_GROUPS:
                    try:
                        await client.send_message(grp, deal_msg)
                        print(f"[FORWARD] Sent top deal to {grp}")
                    except Exception as e:
                        print(f"[FORWARD‑ERR] {grp}: {e}")
        # Done – the orchestrator will call this again later
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(run())
