import { getStore } from "@netlify/blobs";
import path from "path";
import fs from "fs";

const AMAZON_AFF_TAG = Netlify.env.get("AFFILIATE_ID_IN") || "shashwat022-21";

async function resolveShortlink(url) {
  try {
    const resp = await fetch(url, { method: "HEAD", redirect: "follow", signal: AbortSignal.timeout(5000) });
    return resp.url || url;
  } catch {
    return url;
  }
}

function extractAsin(url) {
  const m = url.match(/(?:dp|gp\/product|asin|d|product)\/([A-Z0-9]{10})/i);
  return m ? m[1].toUpperCase() : null;
}

function buildAffiliateUrl(asin, domain, tag) {
  return `https://www.${domain}/dp/${asin}?tag=${tag}`;
}

export default async (request, context) => {
  const reqUrl = new URL(request.url);
  const targetUrl = reqUrl.searchParams.get("url");
  const action = reqUrl.searchParams.get("action");
  let id = reqUrl.searchParams.get("id");
  if (!id) {
    id = reqUrl.pathname.split("/").pop();
  }

  const store = getStore("click-stats");

  // --- 1. Handle Shorten Action ---
  if (action === "shorten" && targetUrl) {
    const shortId = Math.random().toString(36).substring(2, 8);
    await store.setJSON(`map:${shortId}`, targetUrl);
    return new Response(JSON.stringify({ shortUrl: `${reqUrl.origin}/s/${shortId}` }), {
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

  // Already a clean Amazon URL with our tag? Redirect directly.
  if (finalUrl.startsWith('https://www.amazon.') && finalUrl.includes(`tag=${AMAZON_AFF_TAG}`)) {
    return new Response(null, {
      status: 302,
      headers: { "Location": finalUrl }
    });
  }

  const domain = finalUrl.includes("amazon.com") ? "amazon.com" : "amazon.in";
  let finalAmazonUrl;

  // For amzn.to / amzn.in shortlinks: resolve them to extract the ASIN
  if (finalUrl.includes("amzn.to") || finalUrl.includes("amzn.in")) {
    const resolved = await resolveShortlink(finalUrl);
    const asin = extractAsin(resolved);
    if (asin) {
      finalAmazonUrl = buildAffiliateUrl(asin, domain, AMAZON_AFF_TAG);
    } else {
      // If resolution fails, append tag as fallback — Amazon may pass it through
      const sep = resolved.includes("?") ? "&" : "?";
      finalAmazonUrl = `${resolved}${sep}tag=${AMAZON_AFF_TAG}`;
    }
  } else if (finalUrl.includes("amazon.")) {
    const asin = extractAsin(finalUrl);
    if (asin) {
      finalAmazonUrl = buildAffiliateUrl(asin, domain, AMAZON_AFF_TAG);
    } else {
      const sep = finalUrl.includes("?") ? "&" : "?";
      finalAmazonUrl = finalUrl.includes("tag=") ? finalUrl : `${finalUrl}${sep}tag=${AMAZON_AFF_TAG}`;
    }
  } else {
    finalAmazonUrl = `https://www.${domain}/deals?tag=${AMAZON_AFF_TAG}`;
  }

  return new Response(null, {
    status: 302,
    headers: {
      "Location": finalAmazonUrl,
      "Cache-Control": "no-cache, no-store, must-revalidate"
    }
  });
};
