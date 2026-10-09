import asyncio, os, re, json, logging, urllib.request
from datetime import datetime, timedelta, timezone
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


def _channels():
    out = []
    for c in config.get("channels") or []:
        cid = str(c.get("id") or "").strip()
        if not cid:
            continue
        if not cid.startswith("@") and not cid.lstrip("-").isdigit():
            cid = "@" + cid
        out.append({
            "id": cid,
            "content_file": c.get("content_file") or CONTENT_SOURCE,
            "handle": cid[1:] if cid.startswith("@") else cid,
        })
    if not out:
        out = [{"id": CHANNEL_ID, "content_file": CONTENT_SOURCE, "handle": CHANNEL_HANDLE.lstrip("@")}]
    return out


CHANNELS = _channels()
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


def _md_escape(text):
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")


def _fetch_tracker_stats():
    tracker = os.getenv("CLICK_TRACKER_URL", "").strip()
    if not tracker:
        return None
    try:
        req = urllib.request.Request(tracker.rstrip("/") + "/stats", headers={"User-Agent": "smartgahr-report"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data if isinstance(data, dict) and data.get("status") == "success" else None
    except Exception as e:
        log.warning("Tracker stats fetch failed: %s", e)
        return None


def _parse_count(text):
    m = re.match(r"^\s*([\d.]+)\s*([KMB])?", str(text), re.IGNORECASE)
    if not m:
        return None
    try:
        val = float(m.group(1))
    except ValueError:
        return None
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    if m.group(2):
        val *= mult[m.group(2).upper()]
    return int(val)


def _recent_channel_views(limit=5, handle=None):
    """Parse view counts from the public t.me/s preview (no API session needed)."""
    handle = (handle or CHANNEL_HANDLE).lstrip("@")
    try:
        req = urllib.request.Request(
            f"https://t.me/s/{handle}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        raw = re.findall(r'class="tgme_widget_message_views"[^>]*>([^<]+)<', html)
        vals = [v for v in (_parse_count(x) for x in raw) if v is not None]
        return vals[-limit:]
    except Exception as e:
        log.warning("Channel views fetch failed: %s", e)
        return []


def _creators_probe_line():
    creds = os.getenv("CREATORS_CREDENTIALS_CSV", r"D:\Smartgahr-credentials.csv")
    if not os.path.exists(creds):
        return None
    try:
        from creators_api_check import check
        r = check()
    except Exception as e:
        log.warning("Creators API probe failed: %s", e)
        return None
    status = r.get("status", "error")
    if status == "eligible":
        return "🔑 **Creators API**: ✅ LIVE — API unlocked!"
    if status == "not_eligible":
        return "🔑 **Creators API**: ⏳ waiting on sales (10 qualified sales / 30 days)"
    return f"🔑 **Creators API**: ❌ {_md_escape(str(r.get('detail', 'error'))[:80])}"


def _clicks_section():
    stats = _fetch_tracker_stats()
    if not stats:
        return "🖱 **Clicks**: (tracker unavailable)\n"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist = stats.get("history", {}) or {}
    srcs = stats.get("sources", {}) or {}
    totals = srcs.get("totals", {}) or {}
    line = (
        f"🖱 **Clicks**: today {hist.get(today, 0)} · "
        f"7d {sum(hist.values())} · total {stats.get('total_clicks', 0)}\n"
    )
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:5]
    if top:
        parts = ", ".join(f"{_md_escape(s)}: {n}" for s, n in top)
        line += f"📡 **Top sources** (lifetime): {parts}\n"
    return line


async def daily_report():
    today = datetime.now().strftime("%Y-%m-%d")
    members_by = {}
    if BOT_TOKEN:
        try:
            async with Bot(token=BOT_TOKEN) as bot:
                await bot.initialize()
                for ch in CHANNELS:
                    try:
                        members_by[ch["handle"]] = await bot.get_chat_member_count(ch["id"])
                    except Exception as e:
                        log.warning("Member count error for %s: %s", ch["id"], e)
        except Exception as e:
            log.warning("Member count error: %s", e)

    primary_handle = CHANNEL_HANDLE.lstrip("@")
    members = members_by.get(primary_handle)
    gs = load_goal_state()
    delta_str = ""
    if isinstance(members, int):
        prev = gs.get("report_members")
        if isinstance(prev, int):
            d = members - prev
            delta_str = f" ({d:+d} vs last report)"
        gs["report_members"] = members
        save_goal_state(gs)
    members_str = str(members) if members is not None else "N/A"

    count_parts = []
    for ch in CHANNELS:
        try:
            n = len(load_content_items(ch["content_file"]))
        except Exception:
            n = 0
        count_parts.append(f"@{ch['handle']} {n}")

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
    from calendar import monthrange
    _, last_day = monthrange(datetime.now().year, datetime.now().month)
    remaining = last_day - datetime.now().day
    try:
        m = int(members_str)
    except (ValueError, TypeError):
        m = 0
    milestones = [100, 250, 500, 1000, 2500, 5000]
    next_m = next((x for x in milestones if x > m), milestones[-1])
    done = min(m, next_m)
    bar_len = 10
    filled = int(done / next_m * bar_len)
    bar = "▓" * filled + "░" * (bar_len - filled)

    clicks_section = _clicks_section()
    ch_lines = []
    for ch in CHANNELS:
        mv = members_by.get(ch["handle"])
        mv_str = str(mv) if isinstance(mv, int) else "N/A"
        views = _recent_channel_views(5, handle=ch["handle"])
        v_str = ""
        if views:
            avg = sum(views) // len(views)
            v_str = f" · 👀 {', '.join(str(v) for v in views)} (avg {avg})"
        ch_lines.append(f"  • @{ch['handle']}: {mv_str} members{v_str}")
    channels_block = "\n".join(ch_lines)
    probe_line = _creators_probe_line()
    probe_block = f"{probe_line}\n" if probe_line else ""

    report = (
        f"📊 **DAILY REPORT** ({today})\n\n"
        f"👥 **Members**: {members_str}{delta_str} 🎯\n"
        f"📊 **Roadmap**: `{bar}` {m}/{next_m}\n"
        f"   (100 → 250 → 500 → 1000 → 2500 → 5000)\n"
        f"📦 **Content Items**: {' · '.join(count_parts)}\n"
        f"📢 **Channels:**\n{channels_block}\n\n"
        f"{clicks_section}"
        f"{probe_block}\n"
        f"🔗 **Referral Stats:**\n"
        f"  • Links created: {ref_count}\n"
        f"  • Total joins: {join_count}\n\n"
        f"🏆 **Top Referrers:**\n{top_str}\n\n"
        f"---\n*{remaining} days left in {datetime.now().strftime('%B')} — keep growing! 🚀*"
    )
    await send_telegram(report)
    log.info("Daily report sent: members=%s, items=%s", members_str, ", ".join(count_parts))

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
            milestones = [(100, "goal_100_notified"), (250, "goal_250_notified"), (500, "goal_500_notified"), (1000, "goal_1000_notified"), (2500, "goal_2500_notified"), (5000, "goal_5000_notified")]
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
