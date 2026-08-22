"""Validate that every content item and website deal page has a working tracked link.
Usage: python validate_links.py
Exits non-zero if any link is missing its target URL.
"""
import glob
import os
import re
import sys
import logging
from urllib.parse import unquote

log = logging.getLogger("validate_links")

CONTENT_FILES = ["content_home.json", "content.json"]
DEALS_DIR = "website/src/content/deals"
BLOG_DIR = "website/src/content/blog"
MIN_ITEMS = 1


def _has_http_target(link):
    return bool(link and link.strip().startswith("http"))


def _has_tracked_target(link):
    if not link:
        return False
    m = re.search(r"[?&]url=([^&\"]*)", link)
    if not m:
        return False
    target = unquote(m.group(1))
    return bool(target and target.startswith("http"))


def validate_content():
    from data import load_json
    total = 0
    broken = []
    for f in CONTENT_FILES:
        if not os.path.exists(f):
            continue
        data = load_json(f, default={"items": []})
        items = data.get("items", [])
        total += len(items)
        for item in items:
            link = item.get("link", "")
            if not _has_http_target(link):
                broken.append(f"{f}:{str(item.get('title', '?'))[:40]}")
    return total, broken


def validate_website():
    broken = []
    for pattern, label in [(os.path.join(DEALS_DIR, "*.md"), "deal"), (os.path.join(BLOG_DIR, "*.md"), "blog")]:
        for f in glob.glob(pattern):
            content = open(f, encoding="utf-8").read()
            m = re.search(r'buyLink:\s*"([^"]*)"', content)
            link = m.group(1) if m else ""
            if not _has_tracked_target(link):
                broken.append(f"{label}:{os.path.basename(f)}")
    return broken


def main():
    total, broken_content = validate_content()
    broken_web = validate_website()
    problems = broken_content + broken_web
    print(f"Content items: {total} | Broken links: {len(problems)}")
    for p in problems:
        print(f"  BROKEN: {p}")
    if total < MIN_ITEMS:
        print(f"ERROR: only {total} content items found")
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    sys.exit(main())