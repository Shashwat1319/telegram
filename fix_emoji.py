import os
import glob
import re

dir_path = r'd:\Telegram\telegram\website\src\content\blog\*.md'
files = glob.glob(dir_path)

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix the corrupted emoji and text
    content = content.replace('dY"\ufffd GRAB DEAL ON AMAZON NOW dY"\ufffd', '🔥 GRAB DEAL ON AMAZON NOW 🔥')
    content = content.replace('dY"', '🔥')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed {file}')
