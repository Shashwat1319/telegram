import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
d = json.load(open('product.json', encoding='utf-8'))
total = len(d['products'])
with_img = [p for p in d['products'] if p.get('image')]
no_img = [p for p in d['products'] if not p.get('image')]
print(f"Total: {total}")
print(f"With image: {len(with_img)}")
print(f"No image: {len(no_img)}")
if with_img:
    print(f"\n--- Products WITH images ---")
    for p in with_img[:5]:
        print(f"  {p.get('name','')[:50]} | img={str(p.get('image',''))[:60]}")
if no_img:
    print(f"\n--- Products WITHOUT images (cleaning up) ---")
    # Keep only products with images
    d['products'] = with_img
    json.dump(d, open('product.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
    print(f"Cleaned! Now {len(with_img)} products remain.")
