import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get("url");
  const action = url.searchParams.get("action");
  // Netlify rewrites the path to /.netlify/functions/go?id=abcde, so read from searchParams first
  let id = url.searchParams.get("id");
  if (!id) {
    id = url.pathname.split("/").pop();
  }

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

  // --- 3. Track Stats (non-blocking) ---
  const ua = request.headers.get("user-agent") || "";
  const isBot = /bot|spider|crawler|preview|facebookexternalhit|telegrambot|whatsapp|slack|twitter|discord|google/i.test(ua);

  if (!isBot) {
    try {
      const today = new Date().toISOString().split("T")[0];
      const key = `clicks:${today}`;
      let currentCount = (await store.get(key, { type: "json" })) || 0;
      await store.setJSON(key, currentCount + 1);

      let totalClicks = (await store.get("total_clicks", { type: "json" })) || 0;
      await store.setJSON("total_clicks", totalClicks + 1);
    } catch (err) {}
  }

  // --- 4. Build Clean Affiliate URL ---
  const myTag = "shashwat022-21";
  const domain = finalUrl.includes("amazon.com") ? "amazon.com" : "amazon.in";

  const asinMatch = finalUrl.match(/(?:dp|gp\/product|asin|d|product)\/([A-Z0-9]{10})/i);
  let finalAmazonUrl;

  if (asinMatch) {
    const asin = asinMatch[1].toUpperCase();
    finalAmazonUrl = `https://www.${domain}/dp/${asin}?tag=${myTag}`;
  } else if (finalUrl.includes("amazon.") || finalUrl.includes("amzn.")) {
    const sep = finalUrl.includes("?") ? "&" : "?";
    finalAmazonUrl = finalUrl.includes("tag=") ? finalUrl : `${finalUrl}${sep}tag=${myTag}`;
  } else {
    // Fallback: drop affiliate cookie on Today's Deals page
    finalAmazonUrl = `https://www.${domain}/gp/goldbox?tag=${myTag}`;
  }

  // --- 5. Return Bot Redirect or Premium HTML Bridge Page ---
  if (isBot) {
    return new Response(null, {
      status: 302,
      headers: {
        "Location": finalAmazonUrl,
        "Cache-Control": "no-cache, no-store, must-revalidate"
      }
    });
  }

  // Deep Link URI Schemes
  const cleanPath = finalAmazonUrl.replace("https://", "").replace("http://", "");
  const intentUrl = `intent://${cleanPath}#Intent;scheme=https;package=com.amazon.mShop.android.shopping;S.browser_fallback_url=${encodeURIComponent(finalAmazonUrl)};end;`;
  const iosUrl = finalAmazonUrl.replace("https://", "com.amazon.mobile.shopping://");

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Redirecting to Amazon...</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-primary: #ff9900;
            --accent-secondary: #ff5500;
            --success-color: #10b981;
            --glow-color: rgba(255, 153, 0, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            overflow-x: hidden;
            position: relative;
        }

        /* Ambient Glow Backgrounds */
        body::before {
            content: '';
            position: absolute;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, var(--glow-color) 0%, transparent 70%);
            top: 15%;
            left: 10%;
            z-index: 1;
            pointer-events: none;
        }

        body::after {
            content: '';
            position: absolute;
            width: 350px;
            height: 350px;
            background: radial-gradient(circle, rgba(234, 88, 12, 0.1) 0%, transparent 70%);
            bottom: 15%;
            right: 10%;
            z-index: 1;
            pointer-events: none;
        }

        .container {
            width: 100%;
            max-width: 480px;
            z-index: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* Glassmorphism Card */
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2.5rem 2rem;
            width: 100%;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3), 
                        0 0 50px rgba(255, 153, 0, 0.03);
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
        }

        /* Badge */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 153, 0, 0.1);
            border: 1px solid rgba(255, 153, 0, 0.2);
            color: var(--accent-primary);
            padding: 6px 14px;
            border-radius: 100px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 1.5rem;
        }

        .badge svg {
            width: 14px;
            height: 14px;
        }

        /* Animated Loader */
        .loader-wrapper {
            position: relative;
            width: 80px;
            height: 80px;
            margin: 0 auto 1.5rem;
        }

        .loader-ring {
            position: absolute;
            width: 100%;
            height: 100%;
            border: 3px solid rgba(255, 255, 255, 0.03);
            border-top: 3px solid var(--accent-primary);
            border-right: 3px solid var(--accent-secondary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        .loader-icon {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 2rem;
            animation: pulse 1.5s ease-in-out infinite;
        }

        h1 {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
            line-height: 1.3;
        }

        h1 span {
            background: linear-gradient(90deg, var(--accent-primary), #ffa825);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtext {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 2rem;
        }

        /* Progress Bar */
        .progress-container {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 100px;
            margin-bottom: 2rem;
            overflow: hidden;
        }

        .progress-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 100px;
            transition: width 2.5s linear;
        }

        /* Steps */
        .steps {
            text-align: left;
            margin-bottom: 2rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.2rem;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }

        .step {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.88rem;
            color: var(--text-secondary);
            margin-bottom: 0.8rem;
            transition: all 0.3s ease;
        }

        .step:last-child {
            margin-bottom: 0;
        }

        .step-check {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            border: 1.5px solid var(--text-secondary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.65rem;
            color: transparent;
            transition: all 0.3s ease;
        }

        .step.active {
            color: var(--text-primary);
            font-weight: 500;
        }

        .step.active .step-check {
            border-color: var(--accent-primary);
            box-shadow: 0 0 8px var(--glow-color);
        }

        .step.done {
            color: var(--success-color);
        }

        .step.done .step-check {
            border-color: var(--success-color);
            background: var(--success-color);
            color: #fff;
        }

        /* Action Button */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
            border: none;
            color: #ffffff;
            padding: 1.1rem 2rem;
            font-size: 1rem;
            font-weight: 700;
            border-radius: 16px;
            cursor: pointer;
            text-decoration: none;
            box-shadow: 0 8px 24px rgba(255, 85, 0, 0.25), 
                        inset 0 -3px 0 rgba(0, 0, 0, 0.15);
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            margin-bottom: 1.5rem;
            letter-spacing: 0.02em;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(255, 85, 0, 0.35);
        }

        .btn:active {
            transform: translateY(1px);
        }

        .btn svg {
            width: 20px;
            height: 20px;
        }

        /* Instruction guides */
        .guide-box {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.04);
            padding: 1.2rem;
            text-align: left;
            font-size: 0.82rem;
            line-height: 1.5;
            color: var(--text-secondary);
        }

        .guide-title {
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.6rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .guide-title svg {
            width: 16px;
            height: 16px;
            color: var(--accent-primary);
        }

        .guide-steps {
            list-style: none;
        }

        .guide-step {
            margin-bottom: 0.5rem;
            position: relative;
            padding-left: 1.25rem;
        }

        .guide-step:last-child {
            margin-bottom: 0;
        }

        .guide-step::before {
            content: '👉';
            position: absolute;
            left: 0;
            top: 0;
        }

        .guide-step strong {
            color: var(--text-primary);
        }

        .guide-ios, .guide-android {
            display: none;
        }

        /* Manual Fallback Link */
        .fallback-link {
            display: inline-block;
            margin-top: 1.5rem;
            color: var(--text-secondary);
            font-size: 0.8rem;
            text-decoration: underline;
            transition: color 0.2s;
        }

        .fallback-link:hover {
            color: var(--accent-primary);
        }

        .footer {
            margin-top: 2rem;
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.2);
            letter-spacing: 0.02em;
        }

        /* Animations */
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes pulse {
            0% { transform: translate(-50%, -50%) scale(1); }
            50% { transform: translate(-50%, -50%) scale(1.15); }
            100% { transform: translate(-50%, -50%) scale(1); }
        }

        @keyframes pulse-shadow {
            0% { box-shadow: 0 0 0 0 rgba(255, 153, 0, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(255, 153, 0, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 153, 0, 0); }
        }

        .pulse-btn {
            animation: pulse-shadow 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <!-- Badge -->
            <div class="badge">
                <svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fill-rule="evenodd" d="M2.166 4.9L10 1.154l7.834 3.746a1 1 0 01.532.89v5.905a8.005 8.005 0 01-4.887 7.34l-3.146 1.42a1 1 0 01-.866 0l-3.146-1.42A8.005 8.005 0 011.63 11.85V5.79a1 1 0 01.536-.89zM10 3.033L3.63 6.077 10 9.123l6.37-3.046L10 3.033zM3.63 8.307l5.37 2.568v5.992a6.002 6.002 0 01-3.667-5.505V8.307zm7.37 8.56v-5.992l5.37-2.568v3.018a6.002 6.002 0 01-3.667 5.505a.999.999 0 01-1.703.037z" clip-rule="evenodd"></path>
                </svg>
                Verified Student Discount
            </div>

            <!-- Loader -->
            <div class="loader-wrapper">
                <div class="loader-ring"></div>
                <div class="loader-icon">🏷️</div>
            </div>

            <h1 id="headline">Applying <span>Loot Code</span>...</h1>
            <p id="subtext" class="subtext">Applying student affiliate tracking and launching the Amazon app.</p>

            <!-- Progress Bar -->
            <div class="progress-container">
                <div id="progress" class="progress-bar"></div>
            </div>

            <!-- Dynamic Steps -->
            <div class="steps">
                <div id="step-1" class="step active">
                    <span class="step-check">✓</span>
                    <span>Decrypting short link metadata</span>
                </div>
                <div id="step-2" class="step">
                    <span class="step-check">✓</span>
                    <span>Injecting tag: shashwat022-21</span>
                </div>
                <div id="step-3" class="step">
                    <span class="step-check">✓</span>
                    <span>Launching native Amazon app</span>
                </div>
            </div>

            <!-- Launch Button -->
            <a id="redirect-btn" class="btn pulse-btn" href="#">
                <svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 100-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3zM16 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM6.5 18a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"></path>
                </svg>
                OPEN IN AMAZON APP
            </a>

            <!-- Smart Dynamic Guides -->
            <div id="guide-ios" class="guide-box guide-ios">
                <div class="guide-title">
                    <svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                    </svg>
                    How to get maximum cashback on iOS
                </div>
                <ul class="guide-steps">
                    <li class="guide-step">Tap the <strong>three dots (...)</strong> or <strong>compass icon</strong> at the top right of the Telegram screen.</li>
                    <li class="guide-step">Select <strong>"Open in Safari"</strong>.</li>
                    <li class="guide-step">Safari will instantly open the **Amazon App** where you are already logged in to claim!</li>
                </ul>
            </div>

            <div id="guide-android" class="guide-box guide-android">
                <div class="guide-title">
                    <svg fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                    </svg>
                    How to bypass browser sandbox
                </div>
                <ul class="guide-steps">
                    <li class="guide-step">If Android asks, select <strong>Amazon Shopping</strong>.</li>
                    <li class="guide-step">Tap <strong>"Always"</strong> so all future deals open in the app automatically.</li>
                    <li class="guide-step">If the app is not installed, it will open in Chrome seamlessly.</li>
                </ul>
            </div>

            <a id="fallback-link" class="fallback-link" href="#">Open in mobile website browser instead</a>
        </div>

        <div class="footer">
            Secure Redirect System &bull; &copy; Budget Deals India
        </div>
    </div>

    <script>
        const webUrl = "${finalAmazonUrl}";
        const intentUrl = "${intentUrl}";
        const iosUrl = "${iosUrl}";

        // Update URLs on DOM elements
        document.getElementById('fallback-link').href = webUrl;
        
        // --- 1. OS Detection ---
        const ua = navigator.userAgent || navigator.vendor || window.opera;
        const isAndroid = /android/i.test(ua);
        const isIOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;

        // Show guide based on OS
        if (isIOS) {
            document.getElementById('guide-ios').style.display = 'block';
        } else if (isAndroid) {
            document.getElementById('guide-android').style.display = 'block';
        }

        // --- 2. Step Animation ---
        const progress = document.getElementById('progress');
        const step1 = document.getElementById('step-1');
        const step2 = document.getElementById('step-2');
        const step3 = document.getElementById('step-3');
        const headline = document.getElementById('headline');

        // Start progress bar animation
        setTimeout(() => {
            progress.style.width = '100%';
        }, 50);

        // Animate checklist steps
        setTimeout(() => {
            step1.className = 'step done';
            step2.className = 'step active';
            headline.innerHTML = "Injecting <span>Tracking Tag</span>...";
        }, 800);

        setTimeout(() => {
            step2.className = 'step done';
            step3.className = 'step active';
            headline.innerHTML = "Launching <span>Amazon App</span>...";
        }, 1600);

        // --- 3. Redirection Handler ---
        function triggerAppRedirect() {
            if (isAndroid) {
                window.location.href = intentUrl;
            } else if (isIOS) {
                window.location.href = iosUrl;
            } else {
                window.location.href = webUrl;
            }
        }

        // Hook click button
        const btn = document.getElementById('redirect-btn');
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            triggerAppRedirect();
        });

        // Auto-trigger redirection after comfort delay (1.2 seconds)
        let redirectTimeout = setTimeout(() => {
            triggerAppRedirect();
        }, 1200);

        // Fallback Timeout: if we are still on the page after 2.8 seconds, redirect to the browser page.
        setTimeout(() => {
            window.location.href = webUrl;
        }, 2800);
    </script>
</body>
</html>`;

  return new Response(html, {
    status: 200,
    headers: { 
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-cache, no-store, must-revalidate"
    }
  });
};
