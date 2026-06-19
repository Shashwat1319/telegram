import os, json, requests, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

def get_latest_product():
    if not os.path.exists("product.json"): return None
    try:
        data = json.load(open("product.json", encoding="utf-8"))
        for prod in data.get("products", []):
            img = prod.get("image", "")
            if img:
                try:
                    r = requests.head(img, timeout=2)
                    if r.status_code == 200: return prod
                except: pass
        if data["products"]: return data["products"][0]
    except: pass
    return None

def download_image(url):
    try:
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        return Image.open(r.raw).convert("RGBA")
    except: return None

def get_font(size, bold=False):
    name = "Oswald-Bold.ttf" if bold else "Oswald-Regular.ttf"
    if os.path.exists(name):
        try: return ImageFont.truetype(name, size)
        except: pass
    try: return ImageFont.truetype("arial.ttf", size)
    except:
        try: return ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", size)
        except: return ImageFont.load_default()

def wrap_text(text, font, max_w, draw):
    lines, words = [], text.split()
    while words:
        line = ''
        while words and draw.textlength(line + words[0], font=font) <= max_w:
            line += words.pop(0) + ' '
        lines.append(line)
    return lines

def create_video_frame(product):
    bg = (25, 0, 0, 255)
    canvas = Image.new("RGBA", (1080, 1920), bg)
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([(0, 0), (1080, 350)], fill=(200, 20, 20, 255))
    tf = get_font(90, bold=True)
    t = "🔥 LOOT DEAL! 🔥"
    draw.text(((1080 - draw.textlength(t, font=tf)) / 2, 60), t, fill="white", font=tf)

    sf = get_font(60, bold=True)
    st = product.get('discount_percent', '60% OFF')
    draw.text(((1080 - draw.textlength(st, font=sf)) / 2, 200), st, fill="yellow", font=sf)

    desc_y = 420
    img_url = product.get("image", "")
    if img_url:
        img = download_image(img_url)
        if img:
            img.thumbnail((700, 700), Image.Resampling.LANCZOS)
            iw, ih = img.size
            bx1 = (1080 - iw) // 2 - 30
            by1 = 400 - 30
            draw.rounded_rectangle([bx1, by1, bx1 + iw + 60, by1 + ih + 60], radius=30, fill="white")
            canvas.paste(img, ((1080 - iw) // 2, 400), img)
            desc_y = by1 + ih + 70

    nf = get_font(50)
    name = product.get("name", "Amazing Deal")[:80]
    for line in wrap_text(name, nf, 900, draw):
        draw.text(((1080 - draw.textlength(line, font=nf)) / 2, desc_y), line, fill="white", font=nf)
        desc_y += 65

    cy = max(desc_y + 100, 1400)
    pf = get_font(80, bold=True)
    pt = f"Just {product.get('price', 'CHECK')}!"
    draw.text(((1080 - draw.textlength(pt, font=pf)) / 2, cy), pt, fill="#00FF00", font=pf)

    cf = get_font(55, bold=True)
    c1 = "👇 Link in Description 👇"
    draw.text(((1080 - draw.textlength(c1, font=cf)) / 2, cy + 130), c1, fill="white", font=cf)

    c2f = get_font(70, bold=True)
    c2 = "📢 @budgetdeals_india"
    draw.text(((1080 - draw.textlength(c2, font=c2f)) / 2, cy + 220), c2, fill="#00BFFF", font=c2f)

    return canvas.convert("RGB")

def generate_video(frame, output="shorts_deal.mp4", duration=5, fps=30):
    arr = np.array(frame)[:, :, ::-1].copy()
    h, w = arr.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output, fourcc, fps, (w, h))
    for _ in range(duration * fps): video.write(arr)
    video.release()
    print(f"Video saved: {output}")

def write_metadata(product):
    name = product.get("name", "Amazing Deal")[:50]
    title = f"Secret Amazon Glitch 🚨 {name} #shorts"
    desc = f"""🔥 AMAZING LOOT DEAL! 🔥

Product: {product.get('name', '')}
Price: {product.get('price', 'Check')}
Discount: {product.get('discount_percent', '')}

👇 GET THIS DEAL:
Join Telegram: https://t.me/budgetdeals_india

Keywords: amazon deals, budget finds india, student deals, loot deals, amazon price drop"""
    with open("youtube_details.txt", "w", encoding="utf-8") as f:
        f.write(f"--- YOUTUBE TITLE ---\n{title}\n\n--- YOUTUBE DESCRIPTION ---\n{desc}")
    print("Metadata written.")

def main():
    product = get_latest_product()
    if not product: print("No product found."); return
    frame = create_video_frame(product)
    generate_video(frame)
    write_metadata(product)
    print("Done! Ready for upload.")

if __name__ == "__main__":
    main()
