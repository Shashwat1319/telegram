"""Generate clean ZIP for Gumroad delivery. Usage: python package.py"""
import zipfile, os, sys

FILES = [
    'bot.py','feeder.py','poster.py','referral.py','reporting.py',
    'orchestrator.py','group_poster.py','utils.py','data.py','config_loader.py',
    'demo.py','setup.bat','setup.sh',
    'product_home.json','content_home.json',
    '.env.example','config.example.json',
    'README.md','SETUP.md','requirements.txt','.gitignore',
]
for root, dirs, files in os.walk('netlify-redirector'):
    for f in files:
        FILES.append(os.path.join(root, f))
FILES.append('.github/workflows/update_products.yml')

OUT = 'telegram-affiliate-system.zip'
if os.path.exists(OUT): os.remove(OUT)
count = 0
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in FILES:
        if os.path.exists(f):
            zf.write(f, f); count += 1
print(f'Package: {OUT} | Files: {count} | Size: {os.path.getsize(OUT)/1024:.0f} KB')
