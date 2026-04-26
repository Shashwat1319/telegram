import glob

for file in glob.glob(r'd:\Telegram\telegram\website\src\content\blog\*.md'):
    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find the link
    url = ''
    start_idx = content.find('href="') + 6
    end_idx = content.find('"', start_idx)
    if start_idx != 5:
        url = content[start_idx:end_idx]

    # Remove the container block completely from markup
    container_idx = content.find('<div class="mega-buy-btn-container">')
    if container_idx != -1:
        content = content[:container_idx].strip() + '\n'

    # Insert buyLink into frontmatter
    if url and 'buyLink:' not in content:
        parts = content.split('---', 2)
        if len(parts) >= 3:
            parts[1] += f'buyLink: "{url}"\n'
            content = '---'.join(parts)
            
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Fixed frontmatter in {file}')
