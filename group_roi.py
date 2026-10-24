"""Per-group click ROI from tracker stats + posted_products.json.

Joins three data sources:
  - tracker /stats -> sources.totals  (lifetime clicks per src=)
  - joined_groups_state.json          (paused flag, members, send status)
  - posted_products.json              (post counts per group)

Attribution note: group_poster sends src = group.lstrip("@") for username
groups and group[:40] (tracked_link truncates at 40) for invite-link groups.

Usage:
    py group_roi.py             # read-only table
    py group_roi.py --apply     # pause zero-click groups (>=6 posts), unpause clickers
    py group_roi.py --min-posts 6
"""

import argparse
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("group_roi")

STATE_FILE = "joined_groups_state.json"
POSTED_FILE = "posted_products.json"
DEFAULT_MIN_POSTS = 6


def _fetch_tracker_stats():
    import urllib.request
    tracker = os.getenv("CLICK_TRACKER_URL", "").strip()
    if not tracker:
        log.warning("CLICK_TRACKER_URL not set")
        return None
    try:
        req = urllib.request.Request(
            tracker.rstrip("/") + "/stats",
            headers={"User-Agent": "smartgahr-group-roi"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data if isinstance(data, dict) and data.get("status") == "success" else None
    except Exception as e:
        log.warning("Tracker stats fetch failed: %s", e)
        return None


def _src_keys_for(group):
    """Tracker src keys that could map back to this group."""
    keys = {group.lstrip("@")}
    if not group.startswith("@"):
        # invite-link groups: group_poster/tracked_link truncate src to 40 chars
        keys.add(group[:40])
        keys.add(group.lstrip("https://").strip("/"))
    return keys


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def load_post_counts(known_groups):
    """Post counts per group from posted_products.json.

    Keys are "group:product_name", but legacy entries exist that are keyed by
    product name (or URL) alone — only count keys whose group prefix matches a
    group we actually know from joined_groups_state.json."""
    if not os.path.exists(POSTED_FILE):
        return {}, 0
    try:
        with open(POSTED_FILE, encoding="utf-8") as f:
            posted = json.load(f)
    except Exception:
        return {}, 0
    counts = {}
    legacy = 0
    for key in posted:
        group = key.split(":", 1)[0]
        if group in known_groups:
            counts[group] = counts.get(group, 0) + 1
        else:
            legacy += 1
    return counts, legacy


def group_clicks(src_totals):
    """Map each group in state to lifetime clicks + post counts."""
    rows = {}  # group -> {clicks, posts}
    state = load_state()

    # Universe of groups = everything tracked in state (invite links + @usernames).
    all_groups = set(state.keys())
    posts, legacy = load_post_counts(all_groups)
    if legacy:
        log.debug("Ignored %d legacy posted_products keys (not group-keyed)", legacy)

    # Invert src_totals into a lookup once.
    click_map = dict(src_totals or {})

    for g in all_groups:
        clicks = 0
        for key in _src_keys_for(g):
            if key in click_map:
                clicks += int(click_map.pop(key) or 0)
        e = state.get(g) or {}
        rows[g] = {
            "clicks": clicks,
            "posts": posts.get(g, 0),
            "paused": bool(e.get("paused")),
            "members": e.get("members"),
            "quality": e.get("quality"),
            "status": e.get("status"),
        }
    # Any leftover src keys that don't map to a known group — report separately.
    leftovers = {k: v for k, v in click_map.items() if v}
    return rows, leftovers


def apply_pauses(rows, state, min_posts):
    """Pause zero-click groups with enough posts; unpause groups with clicks."""
    changed = []
    for g, r in rows.items():
        e = state.get(g) or {}
        if not e:
            continue
        should_pause = r["posts"] >= min_posts and r["clicks"] == 0 and not r["paused"]
        should_unpause = r["clicks"] > 0 and r["paused"]
        if should_pause:
            e["paused"] = True
            e["paused_at"] = datetime.now(timezone.utc).isoformat()
            e["paused_reason"] = f"{r['posts']} posts, 0 clicks"
            state[g] = e
            changed.append(("PAUSE", g, r["posts"]))
        elif should_unpause:
            e.pop("paused", None)
            e.pop("paused_at", None)
            e.pop("paused_reason", None)
            state[g] = e
            changed.append(("UNPAUSE", g, r["posts"]))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="pause/unpause groups based on ROI")
    ap.add_argument("--min-posts", type=int, default=DEFAULT_MIN_POSTS,
                    help="posts before a zero-click group gets paused (default %d)" % DEFAULT_MIN_POSTS)
    args = ap.parse_args()

    stats = _fetch_tracker_stats()
    src_totals = (stats.get("sources", {}) or {}).get("totals", {}) if stats else {}
    if not stats:
        log.warning("No tracker data — ROI will show 0 clicks for everyone")

    rows, leftovers = group_clicks(src_totals)
    state = load_state()

    if not rows:
        log.info("No groups found in state or posted_products")
        return 0

    # Sort: clickable first (desc), then by posts (desc).
    ordered = sorted(rows.items(), key=lambda kv: (-kv[1]["clicks"], -kv[1]["posts"]))

    print("\n%-40s %7s %7s %8s  %-8s %-8s" % ("GROUP", "POSTS", "CLICKS", "CTR", "PAUSED", "QUALITY"))
    print("-" * 90)
    total_posts = total_clicks = 0
    for g, r in ordered:
        ctr = f"{(r['clicks'] / r['posts'] * 100):.1f}%" if r["posts"] else "—"
        name = g if g.startswith("@") else g[:40]
        print("%-40s %7d %7d %8s  %-8s %-8s" % (
            name, r["posts"], r["clicks"], ctr,
            "yes" if r["paused"] else "",
            r.get("quality") or "",
        ))
        total_posts += r["posts"]
        total_clicks += r["clicks"]
    print("-" * 90)
    ctr_all = f"{(total_clicks / total_posts * 100):.1f}%" if total_posts else "—"
    print("%-40s %7d %7d %8s" % ("TOTAL", total_posts, total_clicks, ctr_all))

    if leftovers:
        print("\n(unmapped src keys with clicks: %s)" % ", ".join(
            f"{k}:{v}" for k, v in sorted(leftovers.items(), key=lambda kv: -kv[1])[:10]
        ))

    if args.apply:
        changed = apply_pauses(rows, state, args.min_posts)
        if changed:
            save_state(state)
            for action, g, n in changed:
                print(f"[{action}] {g} ({n} posts)")
            log.info("Applied %d pause/unpause changes", len(changed))
        else:
            log.info("No pause/unpause changes needed")
    else:
        print("\n(dry run — use --apply to pause/unpause)")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
