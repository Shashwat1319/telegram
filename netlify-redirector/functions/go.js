import { getStore } from "@netlify/blobs";

const TAG = process.env.AMAZON_AFFILIATE_TAG || "shashwat022-21";
// NOTE: Buyers — set AMAZON_AFFILIATE_TAG in Netlify env vars to use your own tag
// Leave unset to keep the default (shashwat022-21) while testing

const ERROR_PAGE = (channelHandle) => `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Oops! Something went wrong</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Verdana, sans-serif;
      background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
      margin: 0;
      padding: 2rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      color: #333;
    }
    .card {
      background: rgba(255, 255, 255, 0.85);
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
      padding: 1.5rem;
      margin: 1rem 0;
      width: 100%;
      max-width: 480px;
      text-align: center;
      backdrop-filter: blur(8px);
    }
    h1 {
      margin-bottom: 0.5rem;
      font-size: 1.8rem;
      color: #d9534f;
    }
    p { margin-bottom: 1rem; }
    .link-btn {
      display: block;
      margin: 0.6rem auto;
      padding: 0.8rem 1.2rem;
      width: 90%;
      max-width: 300px;
      background: #28a745;
      color: #fff;
      text-decoration: none;
      border-radius: 8px;
      transition: transform 0.2s, background 0.2s;
    }
    .link-btn:hover {
      background: #218838;
      transform: translateY(-2px);
    }
    .footer { margin-top: 2rem; font-size: 0.9rem; color: #666; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Oops! Something went wrong 😅</h1>
    <p>Looks like the product link didn't work. Join the channel for more deals!</p>
    <a class="link-btn" href="https://t.me/${channelHandle}" target="_blank">📢 Join Channel</a>
  </div>
  <div class="footer">Automated deal bot — always hunting the best discounts.</div>
</body>
</html>`;

export default async (request, context) => {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get("url");
  const action = url.searchParams.get("action");
  const productId = url.searchParams.get("product") || "unknown";
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
    const channelHandle = process.env.CHANNEL_HANDLE || "smartgahr";
    return new Response(ERROR_PAGE(channelHandle), {
      status: 200,
      headers: { "Content-Type": "text/html" }
    });
  }

  // --- 3. Track Stats per product + daily totals ---
  const ua = request.headers.get("user-agent") || "";
  const isBot = /bot|spider|crawler|preview|facebookexternalhit|telegrambot|whatsapp|slack|twitter|discord|google/i.test(ua);

  if (!isBot) {
    try {
      const today = new Date().toISOString().split("T")[0];
      // Daily total
      const dayKey = `clicks:${today}`;
      let dayCount = (await store.get(dayKey, { type: "json" })) || 0;
      await store.setJSON(dayKey, dayCount + 1);
      // Grand total
      let totalClicks = (await store.get("total_clicks", { type: "json" })) || 0;
      await store.setJSON("total_clicks", totalClicks + 1);
      // Per‑product clicks (lifetime)
      const prodKey = `product:${productId}`;
      let prodCount = (await store.get(prodKey, { type: "json" })) || 0;
      await store.setJSON(prodKey, prodCount + 1);
    } catch (err) {}
  }

  // Direct redirect for already‑clean Amazon URLs (including affiliate tag)
  if (finalUrl.startsWith('https://www.amazon.')) {
    return new Response(null, {
      status: 302,
      headers: { "Location": finalUrl }
    });
  }
  const domain = finalUrl.includes("amazon.com") ? "amazon.com" : "amazon.in";

  const asinMatch = finalUrl.match(/(?:dp|gp\/product|asin|d|product)\/([A-Z0-9]{10})/i);
  let finalAmazonUrl;

  if (asinMatch) {
    const asin = asinMatch[1].toUpperCase();
    finalAmazonUrl = `https://www.${domain}/dp/${asin}?tag=${TAG}`;
  } else if (finalUrl.includes("amzn.in") || finalUrl.includes("amzn.to")) {
    finalAmazonUrl = finalUrl;
  } else if (finalUrl.includes("amazon.")) {
    const sep = finalUrl.includes("?") ? "&" : "?";
    finalAmazonUrl = finalUrl.includes("tag=") ? finalUrl : `${finalUrl}${sep}tag=${TAG}`;
  } else {
    finalAmazonUrl = `https://www.${domain}/deals?tag=${TAG}`;
  }

  // Note: Server-side fetching from Netlify to check for 404s is removed.
  // Amazon's WAF often returns 404/503 for datacenter IPs, which incorrectly 
  // triggered the fallback redirect and sent users to a broken page.

  // --- 5. Preview bots → serve OG-rich HTML page that redirects ---
  // Real users → fast 302 redirect
  if (isBot) {
    const productTitle = url.searchParams.get("title") || "🔥 Hot Deal on Amazon";
    const productPrice = url.searchParams.get("price") || "";
    const productDiscount = url.searchParams.get("discount") || "";
    const productImage = url.searchParams.get("img") || `${url.origin}/og-image.jpg`;
    const displayTitle = productDiscount ? `${productDiscount} OFF — ${productTitle}` : productTitle;
    const displayDesc = productPrice ? `${productTitle} — now at ${productPrice}${productDiscount ? ` (${productDiscount} off)` : ""}. Limited-time deal!` : `Grab this limited-time offer before it's gone! Verified price drop.`;
    const html = `<!DOCTYPE html>
<html><head>
  <meta charset="utf-8">
  <title>${displayTitle}</title>
  <meta property="og:title" content="${displayTitle}">
  <meta property="og:description" content="${displayDesc}">
  <meta property="og:image" content="${productImage}">
  <meta property="og:url" content="${finalAmazonUrl}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Budget Deals India">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${displayTitle}">
  <meta name="twitter:description" content="${displayDesc}">
  <meta name="twitter:image" content="${productImage}">
  <meta http-equiv="refresh" content="2;url=${finalAmazonUrl}">
</head><body>
  <p>Redirecting to Amazon deal... <a href="${finalAmazonUrl}">Click here if not redirected</a></p>
  <script>setTimeout(() => { window.location.href = "${finalAmazonUrl}"; }, 2000);</script>
</body></html>`;
    return new Response(html, {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" }
    });
  }

  // --- 6. Real users → fast 302 redirect ---
  return new Response(null, {
    status: 302,
    headers: {
      "Location": finalAmazonUrl,
      "Cache-Control": "no-cache, no-store, must-revalidate"
    }
  });
};
