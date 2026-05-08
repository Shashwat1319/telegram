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
            --card-bg: rgba(30, 41, 59, 0.8);
            --text: #f8fafc;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', sans-serif;
            background: radial-gradient(circle at top right, #1e293b, #0f172a);
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
            padding: 3rem 2rem;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border-radius: 32px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
            animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .logo {
            font-weight: 800;
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #FF9900 0%, #FFD700 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .verified-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            padding: 6px 14px;
            border-radius: 99px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 2.5rem;
            border: 1px solid rgba(16, 185, 129, 0.3);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .loader-container {
            position: relative;
            width: 64px;
            height: 64px;
            margin: 0 auto 2rem;
        }
        .loader {
            width: 100%;
            height: 100%;
            border: 4px solid rgba(255, 153, 0, 0.1);
            border-left-color: var(--primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        .loader-check {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: var(--primary);
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        h1 { font-size: 1.5rem; margin-bottom: 0.75rem; font-weight: 700; }
        p { color: #94a3b8; font-size: 0.95rem; margin-bottom: 2.5rem; line-height: 1.6; }
        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            background: linear-gradient(to bottom, #FF9900, #FFB347);
            color: #000;
            text-decoration: none;
            padding: 1.1rem;
            border-radius: 16px;
            font-weight: 800;
            font-size: 1.1rem;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 10px 20px -5px rgba(255, 153, 0, 0.4);
            margin-bottom: 1.25rem;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 15px 30px -5px rgba(255, 153, 0, 0.5); }
        .btn:active { transform: translateY(0); }
        .footer-note { font-size: 0.8rem; color: #64748b; font-weight: 500; }
        .secure-icon { vertical-align: middle; margin-right: 4px; opacity: 0.7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Budget Deals</div>
        <div class="verified-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Verified Safe Link
        </div>
        
        <div id="status-container">
            <div class="loader-container">
                <div class="loader"></div>
                <div class="loader-check">
                   <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                </div>
            </div>
            <h1 id="headline">Opening App...</h1>
            <p id="subtext">Securing the best student price. One second...</p>
        </div>

        <a href="${finalUrl}" id="redirect-btn" class="btn">
            CONTINUE TO AMAZON
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </a>
        
        <div class="footer-note">
            <svg class="secure-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            Safe & Secure Redirect
        </div>
    </div>

    <script>
        const targetUrl = "${finalUrl}";
        const asin = "${asin}";
        const tag = "${tag}";
        
        // Smart Deep Linking Strategy
        const isAndroid = /Android/i.test(navigator.userAgent);
        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        const isMobile = isAndroid || isIOS;

        let deepLink = targetUrl;
        
        if (asin && isMobile) {
            if (isAndroid) {
                // Robust Android Intent
                deepLink = "intent://www.amazon.in/dp/" + asin + "/?tag=" + tag + "#Intent;scheme=https;package=com.amazon.mShop.android.shopping;S.browser_fallback_url=" + encodeURIComponent(targetUrl) + ";end";
            } else if (isIOS) {
                // For iOS, the standard URL is often best if Universal Links are set up,
                // but amzn:// works for some specific apps.
                deepLink = "amzn://dp/" + asin + "?tag=" + tag;
            }
        }

        // 1. Immediate attempt for mobile
        if (isMobile) {
            window.location.href = deepLink;
        } else {
            // Instant redirect for Desktop (skip bridge)
            window.location.replace(targetUrl);
        }

        // 2. Faster feedback loop
        setTimeout(() => {
            document.getElementById('headline').innerText = "Almost there!";
            document.getElementById('subtext').innerText = "If the app didn't open automatically, tap below.";
        }, 800);

        // 3. Force fallback after 1.5s (reduced from 2s)
        setTimeout(() => {
            if (isMobile) window.location.href = targetUrl;
        }, 1500);
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
