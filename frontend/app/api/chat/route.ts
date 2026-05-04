import { NextRequest } from "next/server";
import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { randomUUID } from "crypto";

async function* readLines(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      yield line;
    }
  }
  if (buffer) yield buffer;
}

export async function POST(req: NextRequest) {
  const body = await req.json();

  // [v0] Debug: Log incoming request
  console.log("[v0] Chat API called with body:", JSON.stringify(body, null, 2));

  // Construct the backend URL properly
  // In Vercel experimentalServices, the backend is at /api on the same origin
  const backendUrl = new URL("/api/chat", req.url);
  console.log("[v0] Calling backend at:", backendUrl.toString());
  console.log("[v0] Request origin:", req.url);

  let backendRes: Response;
  try {
    backendRes = await fetch(backendUrl.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    console.log("[v0] Backend response status:", backendRes.status);
    console.log("[v0] Backend response headers:", Object.fromEntries(backendRes.headers.entries()));
  } catch (fetchError) {
    console.error("[v0] Fetch to backend failed:", fetchError);
    return new Response(
      JSON.stringify({
        error: "Backend fetch failed",
        details: fetchError instanceof Error ? fetchError.message : String(fetchError),
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }

  if (!backendRes.ok || !backendRes.body) {
    // [v0] Debug: Log error details
    const errorText = await backendRes.text().catch(() => "Could not read error body");
    console.error("[v0] Backend error response:", {
      status: backendRes.status,
      statusText: backendRes.statusText,
      body: errorText,
    });
    return new Response(
      JSON.stringify({
        error: "Backend unavailable",
        status: backendRes.status,
        details: errorText,
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const id = randomUUID();
      writer.write({ type: "text-start", id });

      for await (const line of readLines(backendRes.body!)) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6);
        if (data === "[DONE]" || data.startsWith("[ERROR]")) break;
        // Restore newlines encoded by the backend
        const token = data.replace(/\\n/g, "\n");
        writer.write({ type: "text-delta", id, delta: token });
      }

      writer.write({ type: "text-end", id });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
