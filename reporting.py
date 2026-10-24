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


async def _recent_channel_views(limit=5, handle=None):
    """Fetch recent post views via Telethon (2026-10-14: urllib to t.me/s is
    blocked by the network — MTProto works). Returns oldest→newest views."""
    handle = (handle or CHANNEL_HANDLE).lstrip("@")
    try:
        from dotenv import load_dotenv
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        load_dotenv()
        api_id = os.getenv("API_ID")
        api_hash = os.getenv("API_HASH")
        session = os.getenv("TELEGRAM_SESSION_1")
        if not (api_id and api_hash and session):
            return []
        client = TelegramClient(StringSession(session), int(api_id), api_hash, timeout=30)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return []
            msgs = await client.get_messages(handle, limit=limit)
            vals = [m.views for m in msgs if m and m.views is not None]
            vals.reverse()
            return vals
        finally:
            await client.disconnect()
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
        return "🔑 *Creators API*: ✅ LIVE — API unlocked!"
    if status == "not_eligible":
        return "🔑 *Creators API*: ⏳ waiting on sales (10 qualified sales / 30 days)"
    return f"🔑 *Creators API*: ❌ {_md_escape(str(r.get('detail', 'error'))[:80])}"


def _clicks_section():
    stats = _fetch_tracker_stats()
    if not stats:
        return "🖱 *Clicks*: (tracker unavailable)\n"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist = stats.get("history", {}) or {}
    srcs = stats.get("sources", {}) or {}
    totals = srcs.get("totals", {}) or {}
    last7_keys = [(datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    last7 = sum(int(hist.get(k, 0) or 0) for k in last7_keys)
    line = (
        f"🖱 *Clicks*: today {int(hist.get(today, 0) or 0)} · "
        f"7d {last7} · total {stats.get('total_clicks', 0)}\n"
    )
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:5]
    if top:
        parts = ", ".join(f"{_md_escape(s)}: {n}" for s, n in top)
        line += f"📡 *Top sources* (lifetime): {parts}\n"
    return line


def _group_roi_section():
    """Group funnel health: post/click ROI + pause status (2026-10-24)."""
    try:
        from group_roi import group_clicks
        stats = _fetch_tracker_stats()
        src_totals = (stats.get("sources", {}) or {}).get("totals", {}) if stats else {}
        rows, _leftovers = group_clicks(src_totals or {})
        if not rows:
            return None
        posted = [r for r in rows.values() if r["posts"] > 0]
        paused = sum(1 for r in rows.values() if r["paused"])
        total_posts = sum(r["posts"] for r in rows.values())
        total_clicks = sum(r["clicks"] for r in rows.values())
        top = sorted(
            ((g, r) for g, r in rows.items() if r["clicks"] > 0),
            key=lambda kv: -kv[1]["clicks"],
        )[:5]
        lines = [f"🏘 *Groups*: {len(posted)} posted-to · {paused} paused · "
                 f"{total_posts} posts → {total_clicks} clicks"]
        for g, r in top:
            name = g if g.startswith("@") else g[:30]
            lines.append(f"  • {_md_escape(name)}: {r['clicks']} clicks / {r['posts']} posts")
        return "\n".join(lines) + "\n"
    except Exception as e:
        log.debug("Group ROI section skipped: %s", e)
        return None


def _ht_section():
    """High-ticket track: today's posts vs quota per channel (2026-10-24)."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        parts = []
        for ch in config.get("channels") or []:
            ht_file = ch.get("ht_file")
            if not ht_file:
                continue
            posted_path = ht_file.replace(".json", "_posted.json")
            posted = load_json(posted_path, default={}) if os.path.exists(posted_path) else {}
            n_today = sum(
                1 for v in posted.values()
                if isinstance(v, dict) and str(v.get("last", ""))[:10] == today
            )
            quota = int(ch.get("ht_posts_per_day", 2) or 0)
            handle = str(ch.get("id", "?")).lstrip("@")
            parts.append(f"@{handle} {n_today}/{quota}")
        if not parts:
            return None
        return f"💎 *HT track today*: {' · '.join(parts)}\n"
    except Exception as e:
        log.debug("HT section skipped: %s", e)
        return None


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
    group_section = _group_roi_section()
    if group_section:
        clicks_section += group_section
    ht_line = _ht_section()
    if ht_line:
        clicks_section += ht_line
    ch_lines = []
    for ch in CHANNELS:
        mv = members_by.get(ch["handle"])
        mv_str = str(mv) if isinstance(mv, int) else "N/A"
        views = await _recent_channel_views(5, handle=ch["handle"])
        v_str = ""
        if views:
            avg = sum(views) // len(views)
            v_str = f" · 👀 {', '.join(str(v) for v in views)} (avg {avg})"
        ch_lines.append(f"  • @{ch['handle']}: {mv_str} members{v_str}")
    channels_block = "\n".join(ch_lines)
    probe_line = _creators_probe_line()
    probe_block = f"{probe_line}\n" if probe_line else ""

    report = (
        f"📊 *DAILY REPORT* ({today})\n\n"
        f"👥 *Members*: {members_str}{delta_str} 🎯\n"
        f"📊 *Roadmap*: `{bar}` {m}/{next_m}\n"
        f"   (100 → 250 → 500 → 1000 → 2500 → 5000)\n"
        f"📦 *Content Items*: {' · '.join(count_parts)}\n"
        f"📢 *Channels:*\n{channels_block}\n\n"
        f"{clicks_section}"
        f"{probe_block}\n"
        f"🔗 *Referral Stats:*\n"
        f"  • Links created: {ref_count}\n"
        f"  • Total joins: {join_count}\n\n"
        f"🏆 *Top Referrers:*\n{top_str}\n\n"
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
            # --- KPI goals: clicks/day + PA-API unlock flip ---
            try:
                cfg_goals = {}
                try:
                    from config_loader import load_config
                    cfg_goals = load_config().get("tasks", {}).get("goal_tracker", {})
                except Exception:
                    pass
                click_goals = cfg_goals.get("click_goals", [25, 50, 100])
                stats = _fetch_tracker_stats()
                if stats:
                    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    today_clicks = int((stats.get("history") or {}).get(today, 0) or 0)
                    for i, g in enumerate(click_goals):
                        key = f"goal_clicks_{g}_{today}"
                        if today_clicks >= int(g) and not state.get(key):
                            nxt = str(click_goals[i + 1]) if i + 1 < len(click_goals) else None
                            msg = (f"🖱 *{g} CLICKS TODAY!*\n\n"
                                   f"Current: *{today_clicks}* · lifetime *{stats.get('total_clicks', 0)}*"
                                   + (f"\nNext goal: *{nxt}*" if nxt else " — daily goal smashed! 🚀"))
                            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
                            state[key] = True
                            log.info("Goal %s clicks reached!", g)
                    state = {k: v for k, v in state.items()
                             if not (str(k).startswith("goal_clicks_") and not str(k).endswith(today))}
                creds = os.getenv("CREATORS_CREDENTIALS_CSV", r"D:\Smartgahr-credentials.csv")
                if os.path.exists(creds) and not state.get("paaapi_live"):
                    try:
                        from creators_api_check import check as creators_check
                        if creators_check().get("status") == "eligible":
                            await bot.send_message(
                                chat_id=ADMIN_CHAT_ID,
                                text="🔑 *PA-API UNLOCKED!* 🎉\n\n10 qualified sales hit — Creators API is LIVE!",
                                parse_mode="Markdown")
                            state["paaapi_live"] = True
                            log.info("PA-API eligibility reached!")
                    except Exception as e:
                        log.warning("PA-API goal probe failed: %s", e)
            except Exception as e:
                log.warning("KPI goals check failed: %s", e)

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
