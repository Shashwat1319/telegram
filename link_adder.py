import json, os, threading, webbrowser, logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PRODUCT_FILE = "product.json"
PORT = 8080

products = json.load(open(PRODUCT_FILE(PRODUCT_FILE, encoding="utf-8"))["products"]

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
            # Reload global products
            global products
            products = updated_products
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

server = HTTPServer(('127.0.0.1', PORT), Handler)
log.info("Link Adder running at http://localhost:%d", PORT)
webbrowser.open(f'http://localhost:{PORT}')
server.serve_forever()