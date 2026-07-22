import asyncio, os, logging
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv
from config_loader import load_config
from data import load_json, save_json
from utils import load_content_items

load_dotenv()
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not ADMIN_CHAT_ID:
    log.warning("ADMIN_CHAT_ID not set — admin notifications disabled")
config = load_config()
bot_cfg = config.get("bot", {})
CHANNEL_ID = bot_cfg.get("channel_id", os.getenv("CHANNEL_ID", "@channel"))
CHANNEL_HANDLE = bot_cfg.get("channel_handle", "channel")
CONTENT_SOURCE = config.get("content", {}).get("source_file", "content.json")
GOAL_STATE_FILE = "goal_state.json"

def load_goal_state():
    return load_json(GOAL_STATE_FILE, default={})

def save_goal_state(state):
    if not save_json(GOAL_STATE_FILE, state):
        log.error("Failed to save goal state")
async def send_telegram(msg):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            await bot.initialize()
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        log.error("Failed to send message: %s", e)


async def daily_report():
    today = datetime.now().strftime("%Y-%m-%d")
    members = "N/A"
    if BOT_TOKEN and CHANNEL_ID:
        try:
            async with Bot(token=BOT_TOKEN) as bot:
                await bot.initialize()
                count = await bot.get_chat_member_count(CHANNEL_ID)
                members = str(count)
        except Exception as e:
            log.warning("Member count error: %s", e)
    item_count = len(load_content_items(CONTENT_SOURCE))
    referrals = load_json("referrals.json", default={})
    ref_count = len(referrals)
    join_count = sum(len(r.get("joined", [])) for r in referrals.values())
    top = sorted(referrals.values(), key=lambda r: len(r.get("joined", [])), reverse=True)[:3]
    top_lines = []
    for r in top:
        c = len(r.get("joined", []))
        uid = r.get("creator", "?")
        top_lines.append(f"  • User `{uid}` → {c} joins")
    top_str = "\n".join(top_lines) if top_lines else "  • No referrals yet"
    report = (
        f"📊 **DAILY REPORT** ({today})\n\n"
        f"👥 **Members**: {members}/100 🎯\n"
        f"📦 **Content Items**: {item_count}\n"
        f"📢 **Channel**: @{CHANNEL_HANDLE}\n\n"
        f"🔗 **Referral Stats:**\n"
        f"  • Links created: {ref_count}\n"
        f"  • Total joins: {join_count}\n\n"
        f"🏆 **Top Referrers:**\n{top_str}\n\n"
        f"---\n*{30 - int(today[-2:])} days left in July — keep growing! 🚀*"
    )
    await send_telegram(report)
    log.info("Daily report sent: members=%s, items=%d", members, item_count)

async def check_goal():
    if not BOT_TOKEN or not CHANNEL_ID or not ADMIN_CHAT_ID:
        log.error("Missing configuration in .env")
        return
    state = load_goal_state()
    try:
        async with Bot(token=BOT_TOKEN) as bot:
            await bot.initialize()
            count = await bot.get_chat_member_count(CHANNEL_ID)
            log.info("Current subscriber count: %d", count)
            milestones = [(100, "goal_100_notified"), (500, "goal_500_notified"), (1000, "goal_1000_notified")]
            for milestone, key in milestones:
                if count >= milestone and not state.get(key, False):
                    msg = f"🎊 *{milestone} Subscribers!* 🎊\n\nYour channel has reached *{milestone} subscribers*! 🚀\nCurrent: *{count}*"
                    next_m = next((str(m) for m, _ in milestones if m > milestone), None)
                    if next_m:
                        msg += f"\n\nNext milestone: {next_m}! 🔥"
                    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
                    state[key] = True
                    log.info("Goal %d notified!", milestone)
            state["last_checked_count"] = count
            save_goal_state(state)
    except Exception as e:
        log.error("Error tracking goal: %s", e)


if __name__ == "__main__":
    import sys
    if "--daily" in sys.argv:
        asyncio.run(daily_report())
    elif "--goal" in sys.argv:
        asyncio.run(check_goal())
    else:
        print("Usage: python reporting.py --daily | --goal")
