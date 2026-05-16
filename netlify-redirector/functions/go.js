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

  // Extract ASIN and Force Tag
  let asin = "";
  const myTag = "shashwat022-21";
  
  const asinMatch = finalUrl.match(/(?:dp|gp\/product|asin|d|product)\/([A-Z0-9]{10})/i);
  if (asinMatch) asin = asinMatch[1].toUpperCase();
  
  let cleanUrl = finalUrl.split('?')[0];
  if (asin) cleanUrl = `https://www.amazon.in/dp/${asin}`;
  const finalAmazonUrl = `${cleanUrl}?tag=${myTag}`;

  // --- 4. Premium High-Conversion Bridge ---
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Budget Deals | Redirecting</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: white; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .card { background: #1a1f2e; padding: 2.5rem; border-radius: 1.5rem; box-shadow: 0 20px 50px rgba(0,0,0,0.3); text-align: center; max-width: 350px; width: 90%; border: 1px solid rgba(255,255,255,0.05); }
        .loader { border: 3px solid rgba(255,255,255,0.05); border-top: 3px solid #ff9900; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 1.5rem; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        h1 { font-size: 1.4rem; color: #fff; margin-bottom: 0.5rem; font-weight: 700; }
        p { color: #94a3b8; font-size: 0.9rem; margin-bottom: 2rem; line-height: 1.5; }
        .btn { display: block; background: #ff9900; color: #000; padding: 1rem; border-radius: 12px; text-decoration: none; font-weight: 800; font-size: 1rem; transition: transform 0.2s; }
        .btn:active { transform: scale(0.98); }
        .badge { display: inline-flex; align-items: center; background: rgba(34,197,94,0.1); color: #4ade80; padding: 6px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-bottom: 1.5rem; }
        .badge svg { width: 14px; height: 14px; margin-right: 6px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">
            <svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
            Verified Amazon Associate
        </div>
        <h1>Action Required</h1>
        <p>To get the lowest price and open the <b>Amazon App</b>, you must tap the button below.</p>
        <a href="${finalAmazonUrl}" class="btn" onclick="triggerTap(event)">🔓 UNLOCK DEAL IN APP</a>
    </div>

    <script>
        // We REMOVED the auto-redirect!
        // Why? Because Javascript auto-redirects (window.location) inside Telegram's in-app browser 
        // often FAIL to trigger Android App Links, trapping the user in the web view where they aren't logged in.
        // A physical TAP is required to securely break out of the in-app browser and open the native Amazon app.
        
        function triggerTap(e) {
            // The standard href click will trigger App Links naturally.
            // We add a small visual feedback.
            e.target.innerHTML = "Opening Amazon...";
            e.target.style.background = "#e58a00";
        }
    </script>
</body>
</html>
`;

  return new Response(html, {
    status: 200,
    headers: { "Content-Type": "text/html", "Cache-Control": "no-cache" },
  });
};
