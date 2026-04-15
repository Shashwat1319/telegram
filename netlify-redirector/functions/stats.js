import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  try {
    const store = getStore("click-stats");
    const history = {};
    
    // Fetch counts for the last 7 days
    for (let i = 0; i < 7; i++) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split('T')[0];
      const key = `clicks:${dateStr}`;
      
      const count = await store.get(key, { type: "json" }) || 0;
      history[dateStr] = count;
    }

    const total = await store.get("total_clicks", { type: "json" }) || 0;

    return new Response(JSON.stringify({
      status: "success",
      total_clicks: total,
      history: history
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
