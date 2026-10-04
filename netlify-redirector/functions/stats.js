import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  try {
    const store = getStore("click-stats");
    const history = {};
    const sourcesHistory = {};

    // Fetch counts for the last 7 days
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split('T')[0];
      dates.push(dateStr);
      const key = `clicks:${dateStr}`;

      const count = await store.get(key, { type: "json" }) || 0;
      history[dateStr] = count;

      const srcMap = await store.get(`srcdaily:${dateStr}`, { type: "json" }) || {};
      if (Object.keys(srcMap).length) {
        sourcesHistory[dateStr] = srcMap;
      }
    }

    const total = await store.get("total_clicks", { type: "json" }) || 0;

    // Lifetime clicks per known source
    const sourceTotals = {};
    const index = await store.get("src_index", { type: "json" }) || [];
    for (const src of index) {
      const t = await store.get(`srctotal:${src}`, { type: "json" }) || 0;
      sourceTotals[src] = t;
    }

    return new Response(JSON.stringify({
      status: "success",
      total_clicks: total,
      history: history,
      sources: {
        history: sourcesHistory,
        totals: sourceTotals
      }
    }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(JSON.stringify({ status: "error", message: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
