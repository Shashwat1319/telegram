"""Posts latest deal to Facebook every cycle."""
import subprocess, sys
from datetime import datetime
print(f"[{datetime.now().strftime('%H:%M:%S')}] Posting to Facebook...")
subprocess.run([sys.executable, "fb_bot_post.py"])
