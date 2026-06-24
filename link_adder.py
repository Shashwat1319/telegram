import json, os, threading, webbrowser, logging
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PRODUCT_FILE = "product.json"
EXPIRY_FILE = ".link_adder_expiry"
PORT = 8080

def get_or_create_expiry():
    now = datetime.now()
    if os.path.exists(EXPIRY_FILE):
        try:
            expiry = datetime.fromisoformat(open(EXPIRY_FILE).read().strip())
            if now > expiry:
                remaining = timedelta(0)
            else:
                remaining = expiry - now
        except:
            expiry = now + timedelta(days=7)
            open(EXPIRY_FILE, "w").write(expiry.isoformat())
            remaining = timedelta(days=7)
    else:
        expiry = now + timedelta(days=7)
        open(EXPIRY_FILE, "w").write(expiry.isoformat())
        remaining = timedelta(days=7)
    return expiry, remaining

expiry_date, remaining = get_or_create_expiry()
if remaining.total_seconds() <= 0:
    log.warning("This tool has expired. Deleting itself...")
    os.remove(EXPIRY_FILE)
    os.remove(__file__)
    log.info("Deleted. Thank you!")
    exit()

products = json.load(open(PRODUCT_FILE, encoding="utf-8"))["products"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/?'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(read_html().encode('utf-8'))
        elif self.path == '/api/products':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(products, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/api/expiry':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"expiry": expiry_date.isoformat(), "remaining": int(remaining.total_seconds())}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404')
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else ''
        data = json.loads(body) if body else {}
        if self.path == '/api/save':
            updated_products = data.get('products', [])
            with open(PRODUCT_FILE, 'w', encoding='utf-8') as f:
                json.dump({"products": updated_products}, f, indent=4, ensure_ascii=False)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404')
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def read_html():
    html_path = os.path.join(os.path.dirname(__file__), "link_adder.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()

def auto_delete():
    import time, sys
    now = datetime.now()
    if now >= expiry_date:
        time.sleep(2)
        try:
            os.remove(EXPIRY_FILE)
            os.remove(__file__)
        except:
            pass
        log.info("Tool expired and deleted itself.")
        os._exit(0)

threading.Thread(target=auto_delete, daemon=True).start()
server = HTTPServer(('127.0.0.1', PORT), Handler)
log.info("Link Adder is running!")
log.info("Open http://localhost:%d", PORT)
log.info("Expires: %s", expiry_date.strftime('%d %B %Y, %I:%M %p'))
log.info("Time left: %d days, %d hours", remaining.days, remaining.seconds // 3600)
webbrowser.open(f'http://localhost:{PORT}')
server.serve_forever()
