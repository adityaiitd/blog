import { NextResponse } from "next/server";

export async function POST(request: Request) {
  if (!process.env.OPENAI_API_KEY) return NextResponse.json({ available: false }, { status: 503 });
  const { message, state } = await request.json();
  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "gpt-4.1-mini",
      input: [
        { role: "system", content: "You edit a typed travel itinerary. Return only JSON with a concise reply and an actions array using the supplied TripAction patterns. Never invent IDs; use IDs in state. Maximum 10 actions." },
        { role: "user", content: JSON.stringify({ message, state }) },
      ],
      text: { format: { type: "json_object" } },
    }),
  });
  if (!response.ok) return NextResponse.json({ available: false }, { status: 502 });
  const data = await response.json();
  try {
    const parsed = JSON.parse(data.output_text);
    return NextResponse.json({ available: true, reply: String(parsed.reply), actions: Array.isArray(parsed.actions) ? parsed.actions.slice(0, 10) : [] });
  } catch {
    return NextResponse.json({ available: false }, { status: 502 });
  }
}
