"""Validate that every content item has a working tracked link.
Usage: python validate_links.py
Exits non-zero if any link is missing its target URL.
"""
import os
import sys
import logging

log = logging.getLogger("validate_links")

CONTENT_FILES = ["content_home.json", "content_bdia.json", "content.json"]
MIN_ITEMS = 1


def _has_http_target(link):
    return bool(link and link.strip().startswith("http"))


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


def main():
    total, broken_content = validate_content()
    problems = broken_content
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