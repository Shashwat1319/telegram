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

  // --- 5. Always fast-redirect (no interstitial) ---
  // Interstitial/bridge pages commonly reduce conversions in Telegram → Amazon flows.
  // We still track the click above, then do a clean 302 to the final Amazon URL.
  return new Response(null, {
    status: 302,
    headers: {
      "Location": finalAmazonUrl,
      "Cache-Control": "no-cache, no-store, must-revalidate"
    }
  });
};
