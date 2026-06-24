import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "POST only" }), {
      status: 405,
      headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const { email } = await request.json();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return new Response(JSON.stringify({ error: "Invalid email" }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      });
    }

    const store = getStore("subscribers");
    const subscribers = (await store.get("list", { type: "json" })) || [];

    if (subscribers.includes(email)) {
      return new Response(JSON.stringify({ message: "Already subscribed!" }), {
        headers: { "Content-Type": "application/json" }
      });
    }

    subscribers.push(email);
    await store.setJSON("list", subscribers);

    try {
      const TELEGRAM_BOT_TOKEN = Netlify.env.get("BOT_TOKEN");
      const ADMIN_CHAT_ID = Netlify.env.get("ADMIN_CHAT_ID");
      if (TELEGRAM_BOT_TOKEN && ADMIN_CHAT_ID) {
        const msg = `🎉 New subscriber: ${email} (Total: ${subscribers.length})`;
        await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chat_id: ADMIN_CHAT_ID, text: msg })
        });
      }
    } catch {}

    return new Response(JSON.stringify({ message: "Subscribed!" }), {
      headers: { "Content-Type": "application/json" }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
};
