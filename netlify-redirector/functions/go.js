import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get("url");
  const action = url.searchParams.get("action");
  const id = url.pathname.split("/").pop(); 

  const store = getStore("click-stats");

  // --- 1. Handle Shorten Action ---
  if (action === "shorten" && targetUrl) {
    const shortId = Math.random().toString(36).substring(2, 8);
    await store.setJSON(`map:${shortId}`, targetUrl);
    return new Response(JSON.stringify({ shortUrl: `${url.origin}/s/${shortId}` }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  // --- 2. Resolve Final URL ---
  let finalUrl = targetUrl;
  if (id && id !== "go") {
    const mapped = await store.get(`map:${id}`, { type: "json" });
    if (mapped) finalUrl = mapped;
  }

  if (!finalUrl) {
    return new Response(null, {
      status: 302,
      headers: { "Location": "https://t.me/budgetdeals_india" }
    });
  }

  // --- 3. Track Stats ---
  const ua = request.headers.get("user-agent") || "";
  const isBot = /bot|spider|crawler|preview|facebookexternalhit|telegrambot|whatsapp/i.test(ua);
  
  if (!isBot) {
    try {
      const today = new Date().toISOString().split('T')[0];
      const key = `clicks:${today}`;
      let currentCount = await store.get(key, { type: "json" }) || 0;
      await store.setJSON(key, currentCount + 1);
      
      let totalClicks = await store.get("total_clicks", { type: "json" }) || 0;
      await store.setJSON("total_clicks", totalClicks + 1);
    } catch (err) {}
  }

  // --- 4. Extract ASIN & Smart Fallback Tag Routing ---
  const myTag = "shashwat022-21";
  let asin = "";
  let domain = "amazon.in";
  
  if (finalUrl.includes("amazon.com")) {
    domain = "amazon.com";
  }

  const asinMatch = finalUrl.match(/(?:dp|gp\/product|asin|d|product)\/([A-Z0-9]{10})/i);
  if (asinMatch) {
    asin = asinMatch[1].toUpperCase();
  }

  let finalAmazonUrl = "";
  if (asin) {
    finalAmazonUrl = `https://www.${domain}/dp/${asin}?tag=${myTag}`;
  } else {
    // If the URL is empty, broken, or has no ASIN, fallback to a trending query or Today's Deals
    if (finalUrl.includes("amazon.") && !finalUrl.includes("/#")) {
      const separator = finalUrl.includes("?") ? "&" : "?";
      finalAmazonUrl = finalUrl.includes("tag=") ? finalUrl : `${finalUrl}${separator}tag=${myTag}`;
    } else {
      // High-converting fallback: Today's Deals so the affiliate cookie STILL drops!
      finalAmazonUrl = `https://www.${domain}/gp/goldbox?tag=${myTag}`;
    }
  }

  // --- 5. Premium High-Conversion Bridge HTML ---
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Redirecting to Deal... ⚡</title>
    <!-- Premium Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-color: #060913;
            --card-bg: #0f1424;
            --accent-color: #f59e0b; /* Amazon gold */
            --accent-glow: rgba(245, 158, 11, 0.4);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --success-bg: rgba(34, 197, 94, 0.1);
            --success-text: #4ade80;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 1.5rem;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(245, 158, 11, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(59, 130, 246, 0.05) 0%, transparent 40%);
        }

        .container {
            width: 100%;
            max-width: 440px;
            perspective: 1000px;
        }

        .card {
            background: var(--card-bg);
            border-radius: 24px;
            padding: 2.5rem 2rem;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 
                        0 0 40px 0 rgba(245, 158, 11, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #f59e0b, #3b82f6);
        }

        /* Verified Badge */
        .verified-badge {
            display: inline-flex;
            align-items: center;
            background: var(--success-bg);
            color: var(--success-text);
            padding: 8px 16px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.025em;
            margin-bottom: 2rem;
            border: 1px solid rgba(74, 222, 128, 0.15);
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.05);
        }

        .verified-badge svg {
            width: 16px;
            height: 16px;
            margin-right: 6px;
            flex-shrink: 0;
        }

        /* Animated Loader */
        .loader-container {
            position: relative;
            width: 80px;
            height: 80px;
            margin: 0 auto 2rem;
        }

        .loader-ring {
            border: 4px solid rgba(255, 255, 255, 0.03);
            border-top: 4px solid var(--accent-color);
            border-radius: 50%;
            width: 100%;
            height: 100%;
            animation: spin 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
            box-shadow: 0 0 15px var(--accent-glow);
        }

        .loader-icon {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: var(--accent-color);
            font-size: 1.8rem;
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes pulse {
            0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.8; }
            50% { transform: translate(-50%, -50%) scale(1.1); opacity: 1; }
        }

        /* Typography */
        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 0.75rem;
            letter-spacing: -0.01em;
            line-height: 1.25;
        }

        h1 span {
            background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 2rem;
        }

        p strong {
            color: var(--text-primary);
            font-weight: 600;
        }

        /* Action Button */
        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #060913;
            padding: 1.1rem;
            border-radius: 16px;
            text-decoration: none;
            font-weight: 800;
            font-size: 1.05rem;
            letter-spacing: 0.01em;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 10px 25px -5px rgba(245, 158, 11, 0.3),
                        0 0 0 0px rgba(245, 158, 11, 0.2);
            border: none;
            cursor: pointer;
            outline: none;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 30px -5px rgba(245, 158, 11, 0.4),
                        0 0 0 4px rgba(245, 158, 11, 0.1);
        }

        .btn:active {
            transform: translateY(0);
            box-shadow: 0 5px 10px -2px rgba(245, 158, 11, 0.3);
        }

        .btn svg {
            width: 20px;
            height: 20px;
            margin-right: 8px;
            stroke-width: 2.5;
        }

        /* Dynamic Instruction Cards */
        .instructions {
            margin-top: 2rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.25rem;
            text-align: left;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }

        .instructions-title {
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--text-primary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
        }

        .instructions-title svg {
            width: 14px;
            height: 14px;
            margin-right: 6px;
            color: var(--accent-color);
        }

        .step-list {
            list-style: none;
        }

        .step-item {
            font-size: 0.82rem;
            color: var(--text-secondary);
            line-height: 1.5;
            margin-bottom: 0.5rem;
            position: relative;
            padding-left: 1.25rem;
        }

        .step-item::before {
            content: '👉';
            position: absolute;
            left: 0;
            top: 0;
        }

        .step-item strong {
            color: var(--text-primary);
        }

        .step-item-ios {
            display: none;
        }

        .step-item-android {
            display: none;
        }

        /* Footer */
        .footer {
            margin-top: 1.5rem;
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.25);
            letter-spacing: 0.025em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <!-- Verified Amazon Affiliate Badge -->
            <div class="verified-badge">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.952 11.952 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                </svg>
                Amazon Verified Associate
            </div>

            <!-- Animated Loader Icon -->
            <div class="loader-container">
                <div class="loader-ring"></div>
                <div class="loader-icon">🛒</div>
            </div>

            <!-- Text Content -->
            <h1 id="headline">Opening <span>Amazon App</span>...</h1>
            <p id="subtext">Securing the lowest verified student price & applying discount coupon.</p>

            <!-- Unlock Button -->
            <a href="${finalAmazonUrl}" id="redirect-btn" class="btn" onclick="openAmazon(event)">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"></path>
                </svg>
                <span id="btn-text">OPEN IN AMAZON APP</span>
            </a>

            <!-- Smart Dynamic Instructions -->
            <div class="instructions">
                <div class="instructions-title">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Hostel Life Hack Guide
                </div>
                <ul class="step-list">
                    <li class="step-item step-item-default">We bypass standard browsers to open the <strong>Amazon App</strong> so you stay logged in securely!</li>
                    <li class="step-item step-item-android"><strong>Android Users:</strong> Select <strong>Amazon Shopping</strong> and choose <strong>"Always"</strong> if prompted.</li>
                    <li class="step-item step-item-ios"><strong>iPhone Users:</strong> If the app doesn't open automatically, tap the <strong>three dots (...)</strong> at the top right (or browser compass icon) and tap <strong>'Open in Safari'</strong> to trigger the Amazon app!</li>
                </ul>
            </div>
        </div>

        <div class="footer">
            Secure Redirect Service &bull; &copy; Budget Deals India
        </div>
    </div>

    <script>
        const myTag = "${myTag}";
        const asin = "${asin}";
        const domain = "${domain}";
        const webUrl = "${finalAmazonUrl}";

        // --- 1. Dynamic OS and WebView Detection ---
        const ua = navigator.userAgent || navigator.vendor || window.opera;
        const isAndroid = /android/i.test(ua);
        const isIOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
        
        // Update instruction block based on detected OS
        if (isAndroid) {
            document.querySelectorAll('.step-item-android').forEach(el => el.style.display = 'block');
        } else if (isIOS) {
            document.querySelectorAll('.step-item-ios').forEach(el => el.style.display = 'block');
        }

        // --- 2. Intelligent Redirection Core ---
        function openAmazon(e) {
            if (e) e.preventDefault();
            
            const btn = document.getElementById('redirect-btn');
            const btnText = document.getElementById('btn-text');
            const headline = document.getElementById('headline');
            
            btnText.innerText = "LAUNCHING APP...";
            btn.style.background = "linear-gradient(135deg, #e58a00 0%, #b45309 100%)";
            headline.innerHTML = "Launching <span>Amazon App</span>...";

            if (isAndroid && asin) {
                // High-performance Android Intent. Forces Android OS to bypass in-app browser sandbox 
                // and open the product page directly in the Amazon Shopping app. 
                // Fallback is seamlessly handled if the app is missing.
                const intentUrl = "intent://" + domain + "/dp/" + asin + "/?tag=" + myTag + "#Intent;scheme=https;package=com.amazon.mShop.android.shopping;S.browser_fallback_url=" + encodeURIComponent(webUrl) + ";end;";
                window.location.href = intentUrl;
            } 
            else if (isIOS && asin) {
                // iOS Custom Scheme launch. Bypasses in-app WKWebView and launches the Amazon native app.
                const iosUrl = "com.amazon.mobile.shopping.web://" + domain + "/dp/" + asin + "/?tag=" + myTag;
                
                let fallbackTriggered = false;
                const start = Date.now();
                
                window.location.href = iosUrl;
                
                // Fallback handler: if 1.5 seconds pass and we are still in this browser, redirect to web.
                setTimeout(() => {
                    if (Date.now() - start < 2000 && !fallbackTriggered) {
                        fallbackTriggered = true;
                        window.location.href = webUrl;
                    }
                }, 1500);
            } 
            else {
                // Desktop or no ASIN: normal direct redirect
                window.location.href = webUrl;
            }
        }

        // --- 3. Auto-Trigger Redirection on Load ---
        // We trigger it after a tiny 1-second comfort delay so users see the brand trust elements.
        window.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                openAmazon();
            }, 1000);
        });
    </script>
</body>
</html>
`;

  return new Response(html, {
    status: 200,
    headers: { "Content-Type": "text/html", "Cache-Control": "no-cache" },
  });
};
