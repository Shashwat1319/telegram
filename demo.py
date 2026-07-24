"""
Demo Mode — Dry-run the entire pipeline without posting to Telegram.
Run: python demo.py
"""
import sys, os, json
sys.path.insert(0, '.')
os.chdir('.')
from data import load_json
from utils import tracked_url

SOURCE = 'product_home.json'
print("=" * 60)
print("  TELEGRAM AFFILIATE AUTOMATION SYSTEM — DEMO")
print("=" * 60)
data = load_json(SOURCE, default={"products": []})
products = data.get("products", [])
print(f"\n[1/4] Products loaded: {len(products)}")
print(f"      First product: {products[0]['name'][:50]}...")
content_file = 'content_home.json'
if os.path.exists(content_file):
    data = json.load(open(content_file, 'r', encoding='utf-8'))
    items = data['items']
    print(f"\n[2/4] Content items: {len(items)} ({len(products)}x3)")
    pid = products[0]['name'].lower().replace(' ','-')[:40]
    variants = [i for i in items if pid in i.get('product_id','')]
    if variants:
        print(f"      Sample: {products[0]['name'][:45]}")
        for v in variants:
            print(f"        [{v.get('format','?').upper()}] {v.get('title','')[:50]} | -{v.get('discount_val','?')}%")
else:
    print(f"\n[2/4] Run: python feeder.py --source {SOURCE} --output {content_file}")
print(f"\n[3/4] Affiliate link tracking:")
raw = products[0].get('link', '')
tracked = tracked_url(raw, products[0]['name'].lower().replace(' ','-').replace('/','-')[:30])
print(f"      Tracked: {tracked[:60]}...")
print(f"\n[4/4] Bot commands: /start /deal /topdeal /search <kw> /referral /about /contact")
print(f"\n{'=' * 60}")
print(f"  LIVE EXAMPLE: @smartgahr (Home & Kitchen Deals)")
print(f"  Full guide: SETUP.md")
print(f"{'=' * 60}")
