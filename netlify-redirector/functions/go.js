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
    finalUrl = await store.get(`map:${id}`, { type: "json" });
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
    <title>Redirecting | Budget Deals India</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #FF9900;
            --primary-dark: #e68a00;
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text: #f8fafc;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: var(--text);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            overflow: hidden;
        }
        .container {
            width: 90%;
            max-width: 400px;
            text-align: center;
            padding: 2.5rem;
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.6s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .logo {
            font-weight: 800;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #FF9900, #FFD700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .verified-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(16, 185, 129, 0.1);
            color: #10b981;
            padding: 4px 12px;
            border-radius: 99px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 2rem;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }
        .loader {
            width: 48px;
            height: 48px;
            border: 4px solid rgba(255, 153, 0, 0.1);
            border-left-color: var(--primary);
            border-radius: 50%;
            display: inline-block;
            animation: spin 1s linear infinite;
            margin-bottom: 1.5rem;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        h1 { font-size: 1.25rem; margin-bottom: 0.5rem; font-weight: 700; }
        p { color: #94a3b8; font-size: 0.875rem; margin-bottom: 2rem; line-height: 1.5; }
        .btn {
            display: block;
            width: 100%;
            background: var(--primary);
            color: #000;
            text-decoration: none;
            padding: 1rem;
            border-radius: 12px;
            font-weight: 700;
            font-size: 1rem;
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px 0 rgba(255, 153, 0, 0.39);
            margin-bottom: 1rem;
        }
        .btn:active { transform: scale(0.98); }
        .footer-note { font-size: 0.75rem; color: #64748b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Budget Deals India</div>
        <div class="verified-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Loot Verified
        </div>
        
        <div id="status-container">
            <div class="loader"></div>
            <h1>Opening Amazon App</h1>
            <p>We're safely redirecting you to the best deal. If the app doesn't open, click the button below.</p>
        </div>

        <a href="${finalUrl}" id="redirect-btn" class="btn">CONTINUE TO DEAL</a>
        
        <div class="footer-note">
            ✓ Verified Safe Redirect &bull; Budget Deals India
        </div>
    </div>

    <script>
        const targetUrl = "${finalUrl}";
        const asin = "${asin}";
        const tag = "${tag}";
        
        let deepLink = targetUrl;

        // Smart Deep Linking Strategy
        const isAndroid = /Android/i.test(navigator.userAgent);
        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);

        if (asin) {
            if (isAndroid) {
                // Android Intent: Best way to force app open
                deepLink = "intent://www.amazon.in/dp/" + asin + "/?tag=" + tag + "#Intent;scheme=https;package=com.amazon.mShop.android.shopping;end";
            } else if (isIOS) {
                // iOS: amzn:// scheme is the correct Amazon deep link
                deepLink = "amzn://dp/" + asin + "?tag=" + tag;
            }
        }

        // 1. Log attempt
        console.log("Attempting deep link:", deepLink);

        // 2. Immediate attempt
        window.location.href = deepLink;

        // 3. Update button if it takes too long
        setTimeout(() => {
            document.querySelector('h1').innerText = "Almost there...";
            document.getElementById('redirect-btn').innerText = "OPEN IN AMAZON APP";
        }, 2000);

        // 4. Final fallback (only if user stays on page)
        setTimeout(() => {
            window.location.href = targetUrl;
        }, 2000);
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
