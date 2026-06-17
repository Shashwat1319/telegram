import asyncio, os, random
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION = os.getenv('TELEGRAM_SESSION_1')
CHANNEL_ID = os.getenv('CHANNEL_ID').replace('@', '')

GROWTH_TARGET_GROUPS = [g.strip() for g in os.getenv('GROWTH_TARGET_GROUPS', '').split(',') if g]

from bot_post import generate_viral_message
from referral_manager import generate_referral_link
from telethon.tl.functions.messages import ExportChatInviteRequest
import json

async def _get_invite_link(client: TelegramClient) -> str:
    try:
        result = await client(ExportChatInviteRequest(peer=CHANNEL_ID))
        return result.link
    except Exception as e:
        print(f"Failed to get invite link: {e}")
        return f"https://t.me/{CHANNEL_ID}"

async def _dm_random_members(client: TelegramClient, invite_link: str):
    try:
        participants = await client.get_participants(CHANNEL_ID, limit=200)
    except Exception as e:
        print(f"Failed to fetch participants: {e}")
        return

    random.shuffle(participants)
    for user in participants[:10]:
        try:
            try:
                result = await client(ExportChatInviteRequest(peer=CHANNEL_ID, usage_limit=0))
                personal_link = result.link
            except Exception:
                personal_link = invite_link
            
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
            print(f"[DM-ERR] {user.id}: {e}")
        await asyncio.sleep(random.randint(2, 5))

async def _forward_top_deal(client: TelegramClient):
    if not GROWTH_TARGET_GROUPS:
        return
    import json
    with open('product.json', encoding='utf-8') as f:
        products = json.load(f)
    if not products:
        return
    
    from bot_post import generate_message
    deal_msg = generate_message(products[0])
    
    for grp in GROWTH_TARGET_GROUPS:
        try:
            await client.send_message(grp, deal_msg)
            print(f"[FORWARD] Sent top deal to {grp}")
        except Exception as e:
            print(f"[FORWARD-ERR] {grp}: {e}")

async def run():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()
    try:
        invite_link = await _get_invite_link(client)
        await _dm_random_members(client, invite_link)
        await _forward_top_deal(client)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(run())