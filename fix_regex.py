import glob
import re

for file in glob.glob(r'd:\Telegram\telegram\website\src\content\blog\*.md'):
    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Rewrite the whole HTML block to be perfectly clean
    new_btn = '<div class="mega-buy-btn-container">\n    <a href="{url}" target="_blank" rel="noopener noreferrer" class="mega-buy-btn">🔥 GRAB DEAL ON AMAZON NOW 🔥</a>\n</div>'
    
    def replacer(match):
        return new_btn.format(url=match.group(1))

    # Pattern to match the corrupted container regardless of emojis
    content = re.sub(r'<div class="mega-buy-btn-container">[\s\S]*?<a href="(.*?)"[\s\S]*?</a>\s*</div>', replacer, content)
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
        print(f"Fixed {file}")
