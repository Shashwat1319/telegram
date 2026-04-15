import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get("url");

  if (!targetUrl) {
    return new Response("Missing target URL", { status: 400 });
  }

  try {
    // 1. Get today's date key (YYYY-MM-DD)
    const today = new Date().toISOString().split('T')[0];
    const key = `clicks:${today}`;

    // 2. Increment click count in Netlify Blobs
    const store = getStore("click-stats");
    let currentCount = await store.get(key, { type: "json" }) || 0;
    await store.setJSON(key, currentCount + 1);

    // 3. Optional: Total clicks
    let totalClicks = await store.get("total_clicks", { type: "json" }) || 0;
    await store.setJSON("total_clicks", totalClicks + 1);

    console.log(`[CLICK] ${today}: ${currentCount + 1}`);
  } catch (err) {
    console.error("Error updating click count:", err);
  }

  // 4. Redirect to the target URL
  return new Response(null, {
    status: 302,
    headers: {
      Location: targetUrl,
      "Cache-Control": "no-cache"
    },
  });
};
