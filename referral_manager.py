import os, json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
REFERRAL_REWARD_BASE = int(os.getenv('REFERRAL_REWARD_BASE', '10'))
REFERRAL_TIER_1_THRESHOLD = int(os.getenv('REFERRAL_TIER_1_THRESHOLD', '5'))
REFERRAL_TIER_2_THRESHOLD = int(os.getenv('REFERRAL_TIER_2_THRESHOLD', '10'))

REFERRAL_FILE = 'referrals.json'


def load_referrals():
    if not os.path.exists(REFERRAL_FILE):
        return {}
    try:
        with open(REFERRAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_referrals(data):
    with open(REFERRAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def generate_referral_link(user_id: int) -> str:
    referrals = load_referrals()
    for link, info in referrals.items():
        if info.get('creator') == user_id:
            return link

    async with Bot(token=BOT_TOKEN) as bot:
        await bot.initialize()
        inv = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"referral_{user_id}_{datetime.utcnow().timestamp()}",
            creates_join_request=False,
            expire_date=None,
            member_limit=0
        )
        await bot.shutdown()
        link = inv.invite_link

    referrals[link] = {
        'creator': user_id,
        'created_at': datetime.utcnow().isoformat(),
        'joined': []
    }
    save_referrals(referrals)
    return link


def record_joined_user(invite_link: str, new_user_id: int):
    referrals = load_referrals()
    if invite_link not in referrals:
        return False
    info = referrals[invite_link]
    if new_user_id not in info.get('joined', []):
        info.setdefault('joined', []).append(new_user_id)
        save_referrals(referrals)
        return True
    return False


def get_user_stats(user_id: int):
    referrals = load_referrals()
    for link, info in referrals.items():
        if info.get('creator') == user_id:
            total_joined = len(info.get('joined', []))
            points = total_joined * REFERRAL_REWARD_BASE
            return link, total_joined, points
    return None, 0, 0


def calculate_rewards() -> dict:
    referrals = load_referrals()
    rewards = {}
    for info in referrals.values():
        creator = info.get('creator')
        count = len(info.get('joined', []))
        if count >= REFERRAL_TIER_2_THRESHOLD:
            multiplier = 2.0
        elif count >= REFERRAL_TIER_1_THRESHOLD:
            multiplier = 1.5
        else:
            multiplier = 1.0
        rewards[creator] = rewards.get(creator, 0) + int(count * REFERRAL_REWARD_BASE * multiplier)
    return rewards


if __name__ == '__main__':
    import asyncio
    demo_user = 123456789
    link = asyncio.run(generate_referral_link(demo_user))
    print(f'Referral link for user {demo_user}: {link}')
    print('Current rewards:', calculate_rewards())
