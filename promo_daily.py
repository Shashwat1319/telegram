import os
import sys
import random
import json
import logging
from datetime import datetime, date
from data import load_json, save_json

log = logging.getLogger("promo_daily")

QUEUE_FILE = "promo_queue.md"
STATE_FILE = "promo_state.json"
CONTENT_FILE = "content_home.json"
CHANNEL_LINK = "t.me/smartgahr"

WEEK_TEMPLATES = {
    "W1": [
        "🛒 *Value Post:*\nBhai log, Amazon pe 90% 'deals' fake hote hain:\n1. MRP pehle badha dete hain, phir '70% OFF' likhte hain\n2. Asli price jaanne ke liye camelcamelcamel.com use karo\n3. Discount < 15% = normal price, deal nahi\nMain ye sab check karke hi post karta hoon: {link}",
        "🎁 *Offer Post:*\nAaj ki verified deal: {title}\n💰 {price} (MRP {mrp}, {disc} OFF)\n⭐ {rating}/5 rating\nYe check kiya hua deal hai, fake nahi.\nRoz aisi deals: {link}",
        "🤔 *Question Post:*\nSawaal: Amazon pe aapko sabse zyada fake deals kis category me dikhi?\nReply karo — main results kal share karunga!\n(Daily sachchi deals: {link})",
        "🔥 *Deal Post:*\nAaj ka best find: {title}\n💰 {price} (MRP {mrp}, {disc} OFF)\nRating: {rating}/5\nIsse behtar deal mili ho kisi ko? Comment karo!\nRoz aisi deals: {link}",
    ],
    "W2": [
        "🗳️ *Poll Post:*\nAaj ka poll: Kaunsi category me deals chahiye?\n🛏️ Home & Kitchen\n💡 Electronics\n👕 Fashion\n📱 Gadgets\nVote karo — sabse zyada votes wali category kal! \n(Join: {link})",
        "🧐 *Trust Post:*\n'Ye 70% OFF wala kitchen set sach me deal hai?'\nVerdict: Check kiya — MRP inflate tha. ❌\nIsliye hum sirf 40%+ VERIFIED deals dikhate hain.\nRoz asli deals: {link}",
        "🎁 *Giveaway Teaser:*\n🎁 SmartGahr Weekly Giveaway jaldi aa raha hai!\n₹100 Amazon voucher har hafte 1 winner ko.\nRules tab announce honge jab channel 100 members pe pahunchega.\nAbhi join karo, eligible bano: {link}",
        "🗣️ *Review Post:*\nMaine {title} order kiya tha ({price}).\n1 hafte use kar raha hoon — quality {rating}/5.\nIs price pe best hai, expensive wala utna hi deta hai.\nRoz honest reviews: {link}",
    ],
    "W3": [
        "🔒 *Premium Teaser:*\nKya hai @smartgahrpremium?\n• Roz 2x deals (main channel se zyada)\n• Price-drop ALERTS\n• Exclusive 'mat lo ye' analysis\nUnlock: @Ffzon_bot → /referral → 2 friends!\nMain channel: {link}",
        "🎁 *Referral CTA:*\nFREE PREMIUM — 2 friends ka!\nSecret deals channel + price alerts.\nKaise: @Ffzon_bot → /referral → link share karo → 2 friends join → PREMIUM!\n30 din ka access, share karte raho: {link}",
        "🤝 *Share Post:*\nBhai, maine ek channel join kiya jahan roz sachchi deals aati hain.\nBest part: 2 friends invite karo toh SECRET premium channel unlock!\nJoin karo: {link}",
        "🏆 *Growth Post:*\nChannel 22 → 500 members tak ja raha hai!\nJoin karo early — free premium offers tab tak valid hain jab tak channel chhota hai.\nJaldi aao: {link}",
    ],
}

WEEK_BY_DAY = ["W1", "W1", "W1", "W1", "W2", "W2", "W2", "W2", "W3", "W3", "W3", "W3", "W3", "W2", "W1", "W2", "W3", "W2", "W3", "W1", "W3", "W2", "W1", "W3", "W2", "W3", "W1", "W3", "W2", "W1"]


def load_state():
    return load_json(STATE_FILE, default={})


def save_state(state):
    save_json(STATE_FILE, state)


def get_random_product():
    data = load_json(CONTENT_FILE, default={"items": []})
    items = data.get("items", [])
    if not items:
        return {}

    def _price(p):
        try:
            return float("".join(ch for ch in str(p.get("price", "")) if ch.isdigit() or ch == "."))
        except Exception:
            return 0.0

    items = [i for i in items if 0 < _price(i) <= 999]
    # Prefer pain_fix + trust formats for promo value
    prefs = [i for i in items if i.get("format") in ("pain_fix", "trust_check", "personal_review")]
    pool = prefs or items
    return random.choice(pool) if pool else {}


def generate_post(day_index=None, force=False):
    today = date.today().isoformat()
    state = load_state()
    last_date = state.get("last_date")
    if last_date == today and not force:
        return None  # already generated today

    week = WEEK_BY_DAY[(day_index if day_index is not None else date.today().day) % len(WEEK_BY_DAY)]
    templates = WEEK_TEMPLATES[week]
    used = state.get("used_templates", {}).get(week, [])
    available = [i for i in range(len(templates)) if i not in used]
    if not available:
        available = list(range(len(templates)))
        used = []
    pick = random.choice(available)
    template = templates[pick]

    product = get_random_product()
    title = product.get("title", "Amazon Home Deal")[:80]
    # Strip format label suffix like "— 💡 Problem Solved"
    title = title.split("—")[0].strip()[:80]
    price = product.get("price", "")
    mrp = product.get("mrp", "")
    disc = product.get("discount", "")
    rating = product.get("rating", "4.5★")

    post = template.format(
        link=CHANNEL_LINK,
        title=title,
        price=price,
        mrp=mrp,
        disc=disc,
        rating=rating,
    )

    state["last_date"] = today
    used.append(pick)
    state["used_templates"] = {**state.get("used_templates", {}), week: used}
    state["last_post"] = {"date": today, "week": week, "template": pick}
    save_state(state)

    # Append to queue file (user copy-pastes)
    with open(QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n## {today} — {week} — Post #{pick + 1}\n\n{post}\n\n---\n")
    return post


if __name__ == "__main__":
    import argparse
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate daily promo post")
    parser.add_argument("--force", action="store_true", help="Regenerate even if today exists")
    parser.add_argument("--day", type=int, help="Day index for testing")
    args = parser.parse_args()
    post = generate_post(day_index=args.day, force=args.force)
    if post:
        print("GENERATED:")
        print(post)
    else:
        print(f"Already generated today ({date.today()}). Use --force to override.")