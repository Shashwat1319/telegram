import os
import json
from datetime import datetime
from telegram import Bot, ChatInviteLink

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
REFERRAL_REWARD_BASE = int(os.getenv('REFERRAL_REWARD_BASE', '10'))  # base points per referral
REFERRAL_TIER_1_THRESHOLD = int(os.getenv('REFERRAL_TIER_1_THRESHOLD', '5'))  # referrals needed for 1.5x reward
REFERRAL_TIER_2_THRESHOLD = int(os.getenv('REFERRAL_TIER_2_THRESHOLD', '10'))  # referrals needed for 2x reward

# File to persist referral data
REFERRAL_FILE = 'referrals.json'

def _load_referrals():
    if not os.path.exists(REFERRAL_FILE):
        return {}
    try:
        with open(REFERRAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_referrals(data):
    with open(REFERRAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_referral_link(user_id: int) -> str:
    """Create (or retrieve) a unique invite link for a given user.
    The link is stored in the referrals DB together with the creator's ID.
    """
    referrals = _load_referrals()
    # If the user already has a link, reuse it
    for link, info in referrals.items():
        if info.get('creator') == user_id:
            return link
    # Otherwise create a new invite link via the Bot API
    async def _create_link():
        async with Bot(token=BOT_TOKEN) as bot:
            await bot.initialize()
            # Use the channel's invite link creation (requires admin rights)
            # The link will be permanent and limited to 1 usage per user (default)
            inv: ChatInviteLink = await bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                name=f"referral_{user_id}_{datetime.utcnow().timestamp()}",
                creates_join_request=False,
                expire_date=None,
                member_limit=0
            )
            await bot.shutdown()
            return inv.invite_link
    # Run the async helper synchronously because this module is used in a sync context
    import asyncio
    link = asyncio.run(_create_link())
    # Store the mapping
    referrals[link] = {
        'creator': user_id,
        'created_at': datetime.utcnow().isoformat(),
        'joined': []  # list of user_ids that joined via this link
    }
    _save_referrals(referrals)
    return link

def record_joined_user(invite_link: str, new_user_id: int):
    """Record that a new user joined using a specific invite link.
    This should be called from a handler that processes "chat_join_request" or "new_chat_members" events.
    """
    referrals = _load_referrals()
    if invite_link not in referrals:
        return False
    info = referrals[invite_link]
    if new_user_id not in info.get('joined', []):
        info.setdefault('joined', []).append(new_user_id)
        _save_referrals(referrals)
        return True
    return False

def calculate_rewards() -> dict:
    """Calculate total reward points per creator based on tiered referral counts.
    Returns a dict mapping creator_id -> total_points.
    Tier multipliers:
        * < REFERRAL_TIER_1_THRESHOLD : base reward
        * >= REFERRAL_TIER_1_THRESHOLD and < REFERRAL_TIER_2_THRESHOLD : 1.5x base
        * >= REFERRAL_TIER_2_THRESHOLD : 2x base
    """
    referrals = _load_referrals()
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
    # Simple demo: generate a link for a dummy user and print current rewards
    demo_user = 123456789
    print('Referral link for user', demo_user, ':', generate_referral_link(demo_user))
    print('Current rewards:', calculate_rewards())
