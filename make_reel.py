import os
import copy
import json
import requests
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def get_latest_product():
    """Load the most recent product from product.json."""
    if not os.path.exists("product.json"):
        print("product.json not found!")
        return None
    try:
        with open("product.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if data and "products" in data and len(data["products"]) > 0:
                print(f"Loaded product: {data['products'][0]['name']}")
                return data["products"][0]
    except Exception as e:
        print(f"Error loading product.json: {e}")
    return None

def download_image(url):
    """Download image and return a PIL Image object."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        img = Image.open(response.raw).convert("RGBA")
        print(f"Successfully downloaded image from {url}")
        return img
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def get_font(size, bold=False):
    """Utility to load a font."""
    # Attempt to load standard Windows arial font
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(font_name, size)
    except:
        # Fallback to default if Arial is not found
        try:
            return ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", size)
        except:
            print("Arial not found, using default font (will be small and unstyled).")
            return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    """Word wrapper for drawing long text."""
    lines = []
    words = text.split()
    while words:
        line = ''
        while words and draw.textlength(line + words[0], font=font) <= max_width:
            line = line + (words.pop(0) + ' ')
        lines.append(line)
    return lines

def create_video_frame(product):
    """Create a 1080x1920 image combining text and the product photo."""
    # 1. Create a dark premium red canvas
    bg_color = (25, 0, 0, 255) # Dark Red
    canvas = Image.new("RGBA", (1080, 1920), bg_color)
    draw = ImageDraw.Draw(canvas)
    
    # Draw a gradient or slightly lighter red box at the top
    draw.rectangle([(0, 0), (1080, 400)], fill=(200, 20, 20, 255))
    
    # 2. Add Top Urgent Text
    title_font = get_font(100, bold=True)
    text = "🔥 LOOT DEAL ALERT! 🔥"
    w = draw.textlength(text, font=title_font)
    draw.text(((1080 - w) / 2, 80), text, fill="white", font=title_font)
    
    subtitle_font = get_font(70, bold=True)
    sub_text = "Price Drop of the Month 😱"
    w2 = draw.textlength(sub_text, font=subtitle_font)
    draw.text(((1080 - w2) / 2, 220), sub_text, fill="yellow", font=subtitle_font)

    # 3. Add Product Image
    img_url = product.get("image", "")
    if img_url:
        prod_img = download_image(img_url)
        if prod_img:
            # Resize appropriately
            prod_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            img_w, img_h = prod_img.size
            # Create a white background box for aesthetic
            box_margin = 40
            box_x1 = (1080 - img_w) // 2 - box_margin
            box_y1 = 450 - box_margin
            box_x2 = box_x1 + img_w + box_margin * 2
            box_y2 = 450 + img_h + box_margin * 2
            
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=40, fill="white")
            canvas.paste(prod_img, ((1080 - img_w) // 2, 450), prod_img)
            
            # Start Y position for product desc
            desc_y = box_y2 + 80
    else:
        desc_y = 600
        
    # 4. Add Product Name
    name_font = get_font(55, bold=False)
    raw_name = product.get("name", "Amazing Deal")
    # Clean up name if it's too long
    if len(raw_name) > 80:
        raw_name = raw_name[:77] + "..."
        
    wrapped_name_lines = wrap_text(raw_name, name_font, 900, draw)
    for line in wrapped_name_lines:
        w = draw.textlength(line, font=name_font)
        draw.text(((1080 - w) / 2, desc_y), line, fill="white", font=name_font)
        desc_y += 70

    # 5. Add call to action
    cta_y_offset = max(desc_y + 150, 1450)
    
    price_text = f"Get it at: {product.get('price', 'CHECK LINK')}!"
    price_font = get_font(80, bold=True)
    w_p = draw.textlength(price_text, font=price_font)
    draw.text(((1080 - w_p) / 2, cta_y_offset), price_text, fill="#00FF00", font=price_font)
    
    cta_font = get_font(60, bold=True)
    cta_bottom = get_font(80, bold=True)
    
    t1 = "👇 Click the link in description 👇"
    w_t1 = draw.textlength(t1, font=cta_font)
    draw.text(((1080 - w_t1) / 2, 1650), t1, fill="white", font=cta_font)
    
    t2 = "Join Telegram: @BudgetDealsIndia 🚀"
    w_t2 = draw.textlength(t2, font=cta_bottom)
    draw.text(((1080 - w_t2) / 2, 1750), t2, fill="#00BFFF", font=cta_bottom)
    
    return canvas.convert("RGB")

def generate_video(frame_image, output_filename="shorts_deal.mp4", duration_sec=5, fps=30):
    """Turn the static PIL Frame Image into an MP4 video."""
    print("Generating Video File... This may take a few seconds.")
    # Convert PIL image to cv2 numpy array (BGR instead of RGB)
    open_cv_image = np.array(frame_image) 
    open_cv_image = open_cv_image[:, :, ::-1].copy() 

    height, width, layers = open_cv_image.shape
    
    # Try using 'mp4v' for MP4
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))
    
    total_frames = duration_sec * fps
    for _ in range(total_frames):
        video.write(open_cv_image)

    video.release()
    print(f"Video saved successfully as: {output_filename}")

def write_video_metadata(product):
    """Generate Title, Description and Tags for YouTube Shorts algorithm."""
    name = product.get("name", "Amazing Deal")
    short_name = name[:50] + "..." if len(name) > 50 else name
    
    title = f"Secret Amazon Glitch 🚨 {short_name} #shorts #amazonfinds"
    
    description = f"""🔥 AMAZING LOOT DEAL DETECTED! 🔥

Product: {name}
Price: {product.get('price', 'Check Link')}

👇 GET THIS DEAL HERE BEFORE IT EXPIRES 👇
Join Our Official Telegram Channel: https://t.me/BudgetDealsIndia
Click the link above, we drop these 90% OFF deals directly in Telegram daily!

(Search "@BudgetDealsIndia" on Telegram to join free!)

Keywords / SEO Tags:
amazon gadgets, super cheap amazon finds, amazon glitch today, loot deals india, lowest price online, amazon loot tricks, electronic sales 2026, free products online, flipkart sale hack
"""
    with open("youtube_details.txt", "w", encoding="utf-8") as f:
        f.write("--- YOUTUBE TITLE ---\n")
        f.write(title + "\n\n")
        f.write("--- YOUTUBE DESCRIPTION ---\n")
        f.write(description)
        
    print("Generated SEO Metadata: youtube_details.txt")

def main():
    product = get_latest_product()
    if not product:
        print("Exiting, no product found.")
        return

    frame = create_video_frame(product)
    generate_video(frame)
    write_video_metadata(product)
    print("Done! You can now upload 'shorts_deal.mp4' to YouTube with a trending song.")

if __name__ == "__main__":
    main()
