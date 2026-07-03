import { getStore } from "@netlify/blobs";
import path from "path";
import fs from "fs";

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
    // Load custom error page with affiliate links
    const errorPath = path.resolve(__dirname, '..', 'error_page.html');
    const errorHtml = fs.readFileSync(errorPath, 'utf8');
    return new Response(errorHtml, {
      status: 200,
      headers: { "Content-Type": "text/html" }
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

  // Direct redirect for already‑clean Amazon URLs (including affiliate tag)
  if (finalUrl.startsWith('https://www.amazon.')) {
    return new Response(null, {
      status: 302,
      headers: { "Location": finalUrl }
    });
  }
  const domain = finalUrl.includes("amazon.com") ? "amazon.com" : "amazon.in";

  const TAG = "shashwat022-21";
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
    const ogImage = "https://budgetdeals-tracker-737523f4.netlify.app/og-image.jpg";
    const html = `<!DOCTYPE html>
<html><head>
  <meta charset="utf-8">
  <title>Budget Deals India - Best Amazon Deals</title>
  <meta property="og:title" content="🔥 Hot Deal on Amazon - Budget Deals India">
  <meta property="og:description" content="Grab this limited-time offer before it's gone! Verified price drop.">
  <meta property="og:image" content="${ogImage}">
  <meta property="og:url" content="${finalAmazonUrl}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Budget Deals India">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="🔥 Hot Deal on Amazon - Budget Deals India">
  <meta name="twitter:description" content="Grab this limited-time offer before it's gone! Verified price drop.">
  <meta name="twitter:image" content="${ogImage}">
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
