import asyncio
import os
import json
from telegram import Bot
from dotenv import load_dotenv

# Load configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

STATE_FILE = "goal_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

async def check_goal():
    if not BOT_TOKEN or not CHANNEL_ID or not ADMIN_CHAT_ID:
        print("[ERROR] Missing configuration in .env")
        return

    bot = Bot(token=BOT_TOKEN)
    state = load_state()
    
    try:
        # Get Current Subscriber Count
        count = await bot.get_chat_member_count(CHANNEL_ID)
        print(f"Current Subscriber Count: {count}")
        
        # Check for 100 Members Goal
        if count >= 100 and not state.get("goal_100_notified", False):
            msg = (
                "🎊 *MUBARAK HO!* 🎊\n\n"
                f"Aapne *100 Subscribers* ka milestone touch kar liya hai! 🚀\n"
                f"Current Count: *{count}*\n\n"
                "Aapki mehnat rang la rahi hai. Agla target: 500! 🔥"
            )
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
            state["goal_100_notified"] = True
            print("[OK] Goal 100 Notified!")
            
        # Optional: Track current count in state for history
        state["last_checked_count"] = count
        save_state(state)
        
    except Exception as e:
        print(f"[!] Error tracking goal: {e}")

if __name__ == "__main__":
    asyncio.run(check_goal())
