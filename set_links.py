# -*- coding: utf-8 -*-
"""Fill affiliate links into product.json from diwali_links.txt.

Usage:
  py set_links.py            # fill links, show what's still missing
  py set_links.py --build    # fill, then fetch images + rebuild site

diwali_links.txt format (one product per line):
  Product Name | https://amzn.to/xxxx
Lines without a link (or starting with #) are ignored.
"""
import json, sys, io, os, subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

LINKS_FILE = "diwali_links.txt"
PRODUCTS = "product.json"


def main():
    if not os.path.exists(LINKS_FILE):
        print(f"ERROR: {LINKS_FILE} not found")
        return 1

    filled, bad = {}, []
    with open(LINKS_FILE, encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            name, _, link = line.partition("|")
            name, link = name.strip(), link.strip()
            if not link:
                continue
            if not link.lower().startswith("http"):
                bad.append(f"line {i}: link must start with http -> {link[:50]}")
                continue
            filled[name] = link

    if bad:
        print("PROBLEMS:")
        for b in bad:
            print(" -", b)
        return 1
    if not filled:
        print("No links found in diwali_links.txt yet.")
        return 0

    data = json.load(open(PRODUCTS, encoding="utf-8"))
    by_name = {p["name"].strip().lower(): p for p in data["products"]}
    done, missing = [], []
    for name, link in filled.items():
        p = by_name.get(name.strip().lower())
        if p is None:
            missing.append(name)
            continue
        p["link"] = link
        done.append(name)

    if missing:
        print("Names not found in product.json:")
        for m in missing:
            print(" -", m)
        print("(fix the spelling in diwali_links.txt, then rerun)")

    text = json.dumps(data, ensure_ascii=False, indent=2).replace("\r\n", "\n").replace("\n", "\r\n")
    with open(PRODUCTS, "w", encoding="utf-8", newline="") as f:
        f.write(text + "\r\n")

    raw = data["products"]
    left = sum(1 for p in raw if not (p.get("link") or "").strip())
    print(f"Filled: {len(done)} | still empty: {left}")

    if "--build" in sys.argv and left == 0:
        print("\n[1/2] fetching images...")
        subprocess.run([sys.executable, "fetch_images.py"])
        print("\n[2/2] rebuilding site...")
        subprocess.run([sys.executable, "_site_builder.py"])
        print("Done. Site rebuilt — review with git diff, then commit/push.")
    elif left:
        print("Jab sab links bhar jayen: py set_links.py --build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
