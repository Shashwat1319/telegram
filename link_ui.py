#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Link Filler UI — browser form for product.json affiliate links.

Usage:
  py link_ui.py            # starts http://127.0.0.1:8777 and opens browser

Features:
  - Shows every product whose link is empty (top) with name, price, category
  - Paste affiliate link -> Save -> written into product.json (safe format)
  - "Amazon pe dhundho" button opens an Amazon search for that product
  - "Build site" button runs fetch_images.py + _site_builder.py after save
  - Existing linked products shown collapsed below (read-only count)

Stdlib only. No installs.
"""
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
PRODUCTS = "product.json"
PORT = 8777

BUILD_STATE = {"running": False, "log": "", "done": False}


# ── data helpers ─────────────────────────────────────────────────────────────
def load_products():
    with open(PRODUCTS, encoding="utf-8") as f:
        return json.load(f)["products"]


def save_products(prods):
    data = {"products": prods}
    text = json.dumps(data, ensure_ascii=False, indent=2)
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(PRODUCTS, "w", encoding="utf-8", newline="") as f:
        f.write(text + "\r\n")


def product_rows():
    out = []
    for i, p in enumerate(load_products()):
        link = (p.get("link") or "").strip()
        out.append({
            "idx": i,
            "name": p.get("name", ""),
            "price": p.get("price", ""),
            "mrp": p.get("mrp", ""),
            "discount": p.get("discount_percent", ""),
            "rating": p.get("rating", ""),
            "category": p.get("category", ""),
            "link": link,
        })
    return out


def apply_links(links):
    """links: list of {idx:int, link:str}. Validates + writes product.json."""
    prods = load_products()
    errors, changed = [], 0
    for item in links:
        try:
            idx = int(item.get("idx"))
            url = str(item.get("link") or "").strip()
        except (TypeError, ValueError):
            errors.append("bad row")
            continue
        if not (0 <= idx < len(prods)):
            errors.append(f"row {idx}: out of range")
            continue
        if url and not re.match(r"^https?://", url, re.I):
            errors.append(f"{prods[idx]['name'][:40]}: link http se shuru hona chahiye")
            continue
        if (prods[idx].get("link") or "") != url:
            prods[idx]["link"] = url
            changed += 1
    if changed:
        save_products(prods)
    return changed, errors


def start_build():
    if BUILD_STATE["running"]:
        return
    BUILD_STATE.update(running=True, done=False, log="")
    threading.Thread(target=_run_build, daemon=True).start()


def _run_build():
    steps = [
        ("fetch images", [sys.executable, "fetch_images.py"]),
        ("rebuild site", [sys.executable, "_site_builder.py"]),
    ]
    for label, cmd in steps:
        BUILD_STATE["log"] += f"\n$ {label}: {' '.join(cmd)}\n"
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=900)
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            BUILD_STATE["log"] += out[-4000:] + f"\n[exit {r.returncode}]\n"
            if r.returncode != 0:
                BUILD_STATE["log"] += "STOPPED (error above)\n"
                break
        except Exception as e:
            BUILD_STATE["log"] += f"ERROR: {e}\nSTOPPED\n"
            break
    else:
        BUILD_STATE["log"] += "\nDONE — site rebuilt. git status dekho, commit/push karo.\n"
    BUILD_STATE["running"] = False
    BUILD_STATE["done"] = True


# ── page ─────────────────────────────────────────────────────────────────────
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartGahr — Link Filler</title>
<style>
  :root { --bg:#0f1115; --card:#1a1d24; --line:#2a2f3a; --txt:#e7e9ee;
          --mut:#9aa1af; --acc:#ffb020; --ok:#2ecc71; --bad:#ff5f56; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
         font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
  header { position:sticky; top:0; z-index:5; background:#14171d;
           border-bottom:1px solid var(--line); padding:12px 16px;
           display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  header h1 { font-size:16px; margin:0; }
  .stats { color:var(--mut); font-size:13px; }
  .stats b { color:var(--acc); }
  button { cursor:pointer; border:0; border-radius:8px; padding:9px 14px;
           font-weight:600; font-size:14px; }
  .btn-save { background:var(--ok); color:#06210f; }
  .btn-build { background:var(--acc); color:#251600; }
  button:disabled { opacity:.5; cursor:default; }
  main { max-width:980px; margin:0 auto; padding:14px 14px 80px; }
  .hint { background:#1e2330; border:1px solid var(--line); border-radius:10px;
          padding:10px 12px; color:var(--mut); font-size:13.5px; margin-bottom:14px; }
  .hint code { background:#0f1115; padding:1px 6px; border-radius:5px; color:var(--acc); }
  .row { background:var(--card); border:1px solid var(--line); border-radius:12px;
         padding:12px; margin-bottom:10px; }
  .row.filled { opacity:.55; }
  .name { font-weight:600; margin-bottom:2px; }
  .meta { color:var(--mut); font-size:12.5px; margin-bottom:8px; }
  .meta .cat { color:#7fb3ff; }
  .meta .off { color:var(--ok); font-weight:600; }
  .inrow { display:flex; gap:8px; flex-wrap:wrap; }
  input[type=text] { flex:1 1 320px; min-width:0; background:#0f1115;
         border:1px solid var(--line); border-radius:8px; color:var(--txt);
         padding:10px 12px; font-size:14px; }
  input[type=text]:focus { outline:2px solid var(--acc); border-color:transparent; }
  .find { background:#2a2f3a; color:var(--txt); text-decoration:none;
          padding:10px 12px; border-radius:8px; font-size:13px; white-space:nowrap; }
  .find:hover { background:#363c49; }
  .status { position:fixed; left:0; right:0; bottom:0; background:#14171d;
            border-top:1px solid var(--line); padding:10px 16px; font-size:13px;
            color:var(--mut); display:flex; gap:14px; align-items:center; }
  #log { display:none; background:#0b0d11; border:1px solid var(--line);
         border-radius:10px; padding:10px; margin-top:12px; white-space:pre-wrap;
         font:12px/1.5 ui-monospace,Consolas,monospace; color:#9be89b;
         max-height:300px; overflow:auto; }
  .toast { position:fixed; top:64px; right:14px; background:var(--ok); color:#06210f;
           padding:10px 16px; border-radius:10px; font-weight:600; display:none;
           box-shadow:0 6px 24px rgba(0,0,0,.5); }
  .toast.err { background:var(--bad); color:#fff; }
  h2 { font-size:14px; color:var(--mut); text-transform:uppercase;
       letter-spacing:.06em; margin:22px 0 10px; }
</style>
</head>
<body>
<header>
  <h1>🔗 Link Filler</h1>
  <span class="stats" id="stats"></span>
  <span style="flex:1"></span>
  <button class="btn-save" id="saveBtn" onclick="save()">💾 Save</button>
  <button class="btn-build" id="buildBtn" onclick="build()">🛠 Build site</button>
</header>
<main>
  <div class="hint">
    Har product pe <b>Amazon pe dhundho</b> dabao → product kholo → SiteStripe se
    link copy karo → yahan paste → <b>Save</b>. Sab bhar jayein to <b>Build site</b>
    dabao (images + pages ban jayenge). Phir main commit/push kar dunga — ya khud
    <code>git add product.json netlify-redirector &amp;&amp; git commit -m "links"</code>.
  </div>
  <div id="pending"></div>
  <div id="log"></div>
</main>
<div class="status">
  <span id="buildStatus">build idle</span>
</div>
<div class="toast" id="toast"></div>

<script>
let ROWS = [];

function rowHtml(r, editable) {
  const s = encodeURIComponent(r.name);
  const link = r.link || "";
  return `<div class="row ${editable ? "" : "filled"}">
    <div class="name">${esc(r.name)}</div>
    <div class="meta"><span class="cat">${esc(r.category)}</span> ·
      ${esc(r.price)} <s>${esc(r.mrp)}</s> · <span class="off">${esc(r.discount)} OFF</span> ·
      ★${r.rating} ${link ? " · ✅ linked" : ""}</div>
    <div class="inrow">
      ${editable
        ? `<input type="text" id="in${r.idx}" value="${esc(link)}"
             placeholder="https://amzn.to/xxxx  ya  https://www.amazon.in/dp/..." spellcheck="false">`
        : `<input type="text" value="${esc(link)}" disabled>`}
      <a class="find" target="_blank" rel="noopener"
         href="https://www.amazon.in/s?k=${s}">🔍 Amazon pe dhundho</a>
    </div>
  </div>`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function render(rows) {
  ROWS = rows;
  const pend = rows.filter(r => !r.link);
  const done = rows.filter(r => r.link);
  document.getElementById("pending").innerHTML =
    (pend.length ? `<h2>Links pending (${pend.length})</h2>` : "<h2>✅ Sab links bhar chuke hain!</h2>") +
    pend.map(r => rowHtml(r, true)).join("");
  document.getElementById("stats").innerHTML =
    `linked <b>${done.length}</b> / ${rows.length} · pending <b>${pend.length}</b>`;
}

function toast(msg, err) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (err ? " err" : "");
  t.style.display = "block";
  clearTimeout(t._h);
  t._h = setTimeout(() => (t.style.display = "none"), 3200);
}

async function refresh() {
  try {
    const r = await fetch("/api/products");
    render(await r.json());
  } catch (e) { toast("load failed: " + e, true); }
}

async function save() {
  const links = [];
  for (const r of ROWS) {
    if (r.link) continue;
    const el = document.getElementById("in" + r.idx);
    if (el) links.push({ idx: r.idx, link: el.value.trim() });
  }
  if (!links.length) { toast("Kuch naya paste nahi kiya"); return; }
  const btn = document.getElementById("saveBtn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/save", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ links }),
    });
    const j = await res.json();
    if (j.errors && j.errors.length) {
      toast(j.errors[0], true);
    } else {
      toast(`Saved: ${j.changed} link(s)`);
    }
    await refresh();
  } catch (e) { toast("save failed: " + e, true); }
  btn.disabled = false;
}

async function build() {
  const btn = document.getElementById("buildBtn");
  btn.disabled = true;
  try {
    await fetch("/api/build", { method: "POST" });
    document.getElementById("log").style.display = "block";
    poll();
  } catch (e) { toast("build failed: " + e, true); btn.disabled = false; }
}

async function poll() {
  try {
    const r = await fetch("/api/build");
    const j = await r.json();
    const log = document.getElementById("log");
    log.textContent = j.log || "(running...)";
    log.scrollTop = log.scrollHeight;
    document.getElementById("buildStatus").textContent =
      j.running ? "⏳ build running..." : (j.done ? "✅ build done" : "build idle");
    if (j.running) { setTimeout(poll, 1500); }
    else { document.getElementById("buildBtn").disabled = false; if (j.done) toast("Site rebuild ho gaya!"); }
  } catch (e) { setTimeout(poll, 3000); }
}

refresh();
</script>
</body>
</html>
"""


# ── server ───────────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif self.path == "/api/products":
            self._send(200, json.dumps(product_rows(), ensure_ascii=False))
        elif self.path == "/api/build":
            self._send(200, json.dumps(BUILD_STATE))
        else:
            self._send(404, '{"error":"not found"}')

    def do_POST(self):
        if self.path == "/api/save":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(n) or b"{}")
                changed, errors = apply_links(data.get("links") or [])
                self._send(200, json.dumps({"changed": changed, "errors": errors}))
            except Exception as e:
                self._send(500, json.dumps({"changed": 0, "errors": [str(e)]}))
        elif self.path == "/api/build":
            start_build()
            self._send(200, json.dumps(BUILD_STATE))
        else:
            self._send(404, '{"error":"not found"}')


def main():
    # sanity: file exists and parses
    rows = product_rows()
    pending = sum(1 for r in rows if not r["link"])
    for port in (PORT, PORT + 1, PORT + 2):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    else:
        print("ERROR: ports busy")
        return 1
    url = f"http://127.0.0.1:{port}"
    print(f"Link Filler UI: {url}  ({len(rows)} products, {pending} pending)")
    print("Band karne ke liye: Ctrl+C")
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
