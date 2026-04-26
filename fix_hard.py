import glob

for file in glob.glob(r'd:\Telegram\telegram\website\src\content\blog\*.md'):
    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    if 'mega-buy-btn-container' in content:
        start_idx = content.find('href="') + 6
        end_idx = content.find('"', start_idx)
        if start_idx != 5:
            url = content[start_idx:end_idx]
            container_idx = content.find('<div class="mega-buy-btn-container">')
            if container_idx != -1:
                content = content[:container_idx]
                content += f'<div class="mega-buy-btn-container">\n    <a href="{url}" target="_blank" rel="noopener noreferrer" class="mega-buy-btn">🔥 GRAB DEAL ON AMAZON NOW 🔥</a>\n</div>\n'
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    print(f'Fixed {file}')
