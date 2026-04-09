"""
Facebook Page Token Generator
------------------------------
Run this script, it will open your browser automatically.
Login to Facebook, select your page, and the token will be shown here.
"""
import http.server
import webbrowser
import urllib.parse
import threading

APP_ID = "891489110558398"
REDIRECT_URI = "http://localhost:3000"
SCOPE = "pages_manage_posts"

# OAuth URL
oauth_url = (
    f"https://www.facebook.com/dialog/oauth?"
    f"client_id={APP_ID}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&scope={SCOPE}"
    f"&response_type=token"
)

token_received = threading.Event()

class TokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Send a page that reads the hash fragment and sends it to server
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        if "access_token" in self.path:
            # Token in query params (sometimes happens)
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            token = params.get("access_token", [""])[0]
            if token:
                print(f"\n✅ SUCCESS! Your Page Access Token:\n\n{token}\n")
                print("Copy this token and update your .env file with FB_ACCESS_TOKEN=<token>")
                self.wfile.write(b"<h1>SUCCESS! Check your terminal for the token!</h1>")
                token_received.set()
                return
        
        # Send HTML that extracts token from URL hash and sends to server
        html = """
        <html><body>
        <h2>Fetching your token...</h2>
        <script>
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const token = params.get('access_token');
            if (token) {
                document.body.innerHTML = '<h1>SUCCESS! Check your terminal for the token!</h1>';
                // Send token to local server
                fetch('/token?access_token=' + token);
            } else {
                document.body.innerHTML = '<h1>Error: No token found. Try again.</h1>';
            }
        </script>
        </body></html>
        """.encode()
        self.wfile.write(html)
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def start_server():
    server = http.server.HTTPServer(("localhost", 3000), TokenHandler)
    server.handle_request()  # Handle the initial redirect
    server.handle_request()  # Handle the token fetch request
    server.server_close()

print("🚀 Starting local server on http://localhost:3000")
print("📱 Opening Facebook login in your browser...")
print("➡️  Login to Facebook and select your 'budgetdealsindia' page")
print("⏳ Waiting for token...\n")

# Start server in thread
server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()

# Open browser
webbrowser.open(oauth_url)

# Wait for token
server_thread.join(timeout=120)
print("\nDone! If you see the token above, copy it to your .env file as FB_ACCESS_TOKEN=<token>")
