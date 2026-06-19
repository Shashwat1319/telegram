from PIL import Image

def main():
    banner_path = "channel_banner.png"
    output_path = "channel_banner_processed.png"
    
    print(f"Loading original banner: {banner_path}")
    img = Image.open(banner_path)
    
    # 1. Get the background color from top-left corner
    bg_color = img.getpixel((5, 5))
    print(f"Detected background color: {bg_color}")
    
    # 2. Create a new canvas of size 2560x1440 with the background color
    canvas = Image.new("RGB", (2560, 1440), bg_color)
    
    # 3. Resize the square image to 1440x1440
    img_resized = img.resize((1440, 1440), Image.Resampling.LANCZOS)
    
    # 4. Paste the resized image in the center of the canvas
    # X offset: (2560 - 1440) // 2 = 560
    # Y offset: 0
    canvas.paste(img_resized, (560, 0))
    
    # 5. Save the final banner
    canvas.save(output_path, "PNG")
    print(f"[SUCCESS] Processed banner saved to {output_path} (Size: 2560x1440)")

if __name__ == "__main__":
    main()
