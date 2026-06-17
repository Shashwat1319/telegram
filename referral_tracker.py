import asyncio
import os
import json
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import UpdateBotCallbackQuery, ChatInviteImporter
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION = os.getenv('TELEGRAM_SESSION_1')
CHANNEL_ID = os.getenv('CHANNEL_ID')
REFERRAL_FILE = 'referrals.json'

def load_referrals():
    if os.path.exists(REFERRAL_FILE):
        try:
            with open(REFERRAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_referrals(data):
    with open(REFERRAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def record_join(invite_link: str, user_id: int, username: str = None):
    """Record that a user joined via a specific invite link."""
    referrals = load_referrals()
    
    # Find the referral link (handle both full and partial matches)
    matched_link = None
    for link in referrals:
        if invite_link in link or link in invite_link:
            matched_link = link
            break
    
    if not matched_link:
        # Fallback: check if any link matches the channel
        for link in referrals:
            if CHANNEL_ID.replace('@', '') in link:
                matched_link = link
                break
    
    if matched_link:
        info = referrals[matched_link]
        if user_id not in info.get('joined', []):
            info.setdefault('joined', []).append(user_id)
            info['last_join'] = {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.utcnow().isoformat()
            }
            save_referrals(referrals)
            print(f"[REFERRAL] User {user_id} (@{username}) joined via {matched_link[:50]}... Total: {len(info['joined'])}")
            return True
    return False

from datetime import datetime

async def main():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()
    
    me = await client.get_me()
    print(f"[*] Referral tracker started as {me.first_name} (@{me.username})")
    
    @client.on(events.ChatAction)
    async def handler(event):
        # Handle user joining via invite link
        if event.user_joined or event.user_added:
            user = await event.get_user()
            if user and not user.bot:
                # Try to get the invite link used
                invite_link = None
                if hasattr(event.action, 'invite') and event.action.invite:
                    invite_link = event.action.invite.link
                
                # If no invite link in event, check recent referrals
                if not invite_link:
                    referrals = load_referrals()
                    if referrals:
                        invite_link = list(referrals.keys())[0]  # fallback
                
                record_join(invite_link or '', user.id, user.username)
    
    @client.on(events.Raw)
    async def raw_handler(update):
        # Handle chat_join_request (for channels with join requests enabled)
        if hasattr(update, 'user_id') and hasattr(update, 'invite'):
            invite_link = update.invite.link if update.invite else None
            record_join(invite_link or '', update.user_id)
    
    print("[*] Listening for join events... (Ctrl+C to stop)")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())