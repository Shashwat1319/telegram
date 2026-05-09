import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get("url");
  const action = url.searchParams.get("action");
  const id = url.pathname.split("/").pop(); // Get ID from /s/:id

  const store = getStore("click-stats");

  // --- 1. Handle Shorten Action (Bot calls this) ---
  if (action === "shorten" && targetUrl) {
    const shortId = Math.random().toString(36).substring(2, 8);
    await store.setJSON(`map:${shortId}`, targetUrl);
    return new Response(JSON.stringify({ shortUrl: `${url.origin}/s/${shortId}` }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  // --- 2. Handle /s/:id Redirect ---
  let finalUrl = targetUrl;
  if (id && id !== "go") {
    const mapped = await store.get(`map:${id}`, { type: "json" });
    if (mapped) finalUrl = mapped;
  }

  if (!finalUrl) {
    return new Response("URL Not Found or Missing. Use /go?url=... or /s/:id", { status: 404 });
  }

  // --- 3. Track Stats ---
  try {
    const today = new Date().toISOString().split('T')[0];
    const key = `clicks:${today}`;
    let currentCount = await store.get(key, { type: "json" }) || 0;
    await store.setJSON(key, currentCount + 1);

    let totalClicks = await store.get("total_clicks", { type: "json" }) || 0;
    await store.setJSON("total_clicks", totalClicks + 1);
  } catch (err) {
    console.error("Error updating click count:", err);
  }

  // Extract ASIN and Tag for better deep linking
  let asin = "";
  let tag = "shashwat022-21";
  
  const asinMatch = finalUrl.match(/(?:dp|gp\/product|asin|d|product)\/([A-Z0-9]{10})/i);
  if (asinMatch) asin = asinMatch[1].toUpperCase();
  
  const tagMatch = finalUrl.match(/tag=([^&]+)/);
  if (tagMatch) tag = tagMatch[1];

  // --- 4. Return a Deep-Linking Bridge Page ---
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Gateway | Budget Deals</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #FF9900;
            --accent: #FFD700;
            --bg: #0b0f19;
            --card: rgba(23, 32, 53, 0.95);
            --text: #ffffff;
            --muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg);
            background-image: 
                radial-gradient(at 0% 0%, rgba(255, 153, 0, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(15, 23, 42, 1) 0px, transparent 50%);
            color: var(--text);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            width: 100%;
            max-width: 420px;
            background: var(--card);
            backdrop-filter: blur(20px);
            border-radius: 32px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 40px 30px;
            text-align: center;
            box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.5);
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
        }
        .brand {
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -1px;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .brand span { color: var(--primary); }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(34, 197, 94, 0.1);
            color: #4ade80;
            padding: 8px 16px;
            border-radius: 99px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-bottom: 24px;
            border: 1px solid rgba(34, 197, 94, 0.2);
            text-transform: uppercase;
        }

        .product-circle {
            width: 80px;
            height: 80px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 50%;
            margin: 0 auto 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px dashed rgba(255, 153, 0, 0.3);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); border-color: rgba(255, 153, 0, 0.3); }
            50% { transform: scale(1.05); border-color: rgba(255, 153, 0, 0.6); }
            100% { transform: scale(1); border-color: rgba(255, 153, 0, 0.3); }
        }

        h1 { font-size: 1.5rem; margin-bottom: 12px; font-weight: 700; }
        p { color: var(--muted); font-size: 0.9rem; line-height: 1.6; margin-bottom: 32px; }

        .btn {
            display: block;
            background: linear-gradient(135deg, #FF9900 0%, #FFB347 100%);
            color: #000;
            text-decoration: none;
            padding: 18px;
            border-radius: 18px;
            font-weight: 800;
            font-size: 1.1rem;
            transition: all 0.3s ease;
            box-shadow: 0 15px 30px -5px rgba(255, 153, 0, 0.4);
            margin-bottom: 16px;
        }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 20px 40px -5px rgba(255, 153, 0, 0.5); }
        
        .trust-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }
        .trust-item {
            font-size: 0.7rem;
            color: var(--muted);
            display: flex;
            align-items: center;
            gap: 4px;
            justify-content: center;
        }
        .loading-bar {
            height: 3px;
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 32px;
        }
        .loading-progress {
            height: 100%;
            width: 0%;
            background: var(--primary);
            animation: load 1.5s forwards;
        }
        @keyframes load { to { width: 100%; } }
    </style>
</head>
<body>
    <div class="card">
        <div class="brand">Budget<span>Deals</span></div>
        
        <div class="status-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Amazon Verified Link
        </div>

        <div class="product-circle">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#FF9900" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
        </div>

        <h1 id="title">Opening App...</h1>
        <p id="desc">Connecting to Amazon Secure Server to verify student price...</p>

        <div class="loading-bar">
            <div class="loading-progress"></div>
        </div>

        <a href="${finalUrl}" class="btn" id="main-btn">OPEN AMAZON APP</a>

        <div class="trust-grid">
            <div class="trust-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                SSL Secured
            </div>
            <div class="trust-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                Deal Active
            </div>
        </div>
    </div>

    <script>
        const targetUrl = "${finalUrl}";
        const asin = "${asin}";
        const tag = "${tag}";
        
        const isAndroid = /Android/i.test(navigator.userAgent);
        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        
        let deepLink = targetUrl;
        
        if (asin) {
            if (isAndroid) {
                // FIXED INTENT SYNTAX: Removed the slash before the query string
                deepLink = "intent://www.amazon.in/dp/" + asin + "?tag=" + tag + "#Intent;scheme=https;package=com.amazon.mShop.android.shopping;S.browser_fallback_url=" + encodeURIComponent(targetUrl) + ";end";
            } else if (isIOS) {
                // iOS uses universal links usually, but amzn:// is a fallback
                deepLink = "amzn://dp/" + asin + "?tag=" + tag;
            }
        }

        // 1. Immediate Deep Link Attempt
        if (isAndroid || isIOS) {
            window.location.href = deepLink;
        } else {
            // Desktop: Instant redirect
            window.location.replace(targetUrl);
        }

        // 2. UI Updates for Users Still on Page
        setTimeout(() => {
            document.getElementById('title').innerText = "Almost There!";
            document.getElementById('desc').innerText = "If the Amazon app didn't open automatically, click the button below.";
            document.getElementById('main-btn').innerText = "CLICK TO CONTINUE";
        }, 1500);

        // 3. Last Resort Fallback (Mobile Web)
        setTimeout(() => {
             // Only redirect if the user is still on this page (meaning app didn't open)
             if (isAndroid || isIOS) {
                 window.location.href = targetUrl;
             }
        }, 3000);
    </script>
</body>
</html>
`;

  return new Response(html, {
    status: 200,
    headers: {
      "Content-Type": "text/html",
      "Cache-Control": "no-cache"
    },
  });
};
