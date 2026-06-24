import asyncio, os, json, logging
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

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
        log.error("Missing configuration in .env")
        return

    bot = Bot(token=BOT_TOKEN)
    state = load_state()

    try:
        count = await bot.get_chat_member_count(CHANNEL_ID)
        log.info("Current subscriber count: %d", count)

        if count >= 100 and not state.get("goal_100_notified", False):
            msg = (
                "🎊 *MUBARAK HO!* 🎊\n\n"
                f"Aapne *100 Subscribers* ka milestone touch kar liya hai! 🚀\n"
                f"Current Count: *{count}*\n\n"
                "Aapki mehnat rang la rahi hai. Agla target: 500! 🔥"
            )
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
            state["goal_100_notified"] = True
            log.info("Goal 100 notified!")

        state["last_checked_count"] = count
        save_state(state)

    except Exception as e:
        log.error("Error tracking goal: %s", e)

if __name__ == "__main__":
    asyncio.run(check_goal())
