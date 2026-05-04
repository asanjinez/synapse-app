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

  // [v0] Debug logging
  console.log("[v0] Frontend /api/chat called");
  console.log("[v0] Messages count:", body.messages?.length);
  console.log("[v0] BACKEND_URL env:", process.env.BACKEND_URL);

  // Call the Python backend using inter-service communication
  // The backend has routePrefix "/backend", and the FastAPI route is "/chat"
  // So the full path is /backend/chat
  
  let backendUrl: string;
  
  if (process.env.BACKEND_URL) {
    // If Vercel sets BACKEND_URL for inter-service communication
    backendUrl = `${process.env.BACKEND_URL}/chat`;
    console.log("[v0] Using BACKEND_URL env var");
  } else {
    // Fallback: construct the URL from the current request
    // In production, this will be the same domain with /backend prefix
    const protocol = req.headers.get("x-forwarded-proto") || "https";
    const host = req.headers.get("x-forwarded-host") || req.headers.get("host") || "localhost:3000";
    backendUrl = `${protocol}://${host}/backend/chat`;
    console.log("[v0] Constructed backend URL from request headers");
  }
  
  console.log("[v0] Calling Python backend at:", backendUrl);

  let backendRes: Response;
  try {
    backendRes = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    console.log("[v0] Backend response status:", backendRes.status);
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
    const errorText = await backendRes.text().catch(() => "Could not read error body");
    console.error("[v0] Backend error:", backendRes.status, errorText);
    return new Response(
      JSON.stringify({
        error: "Backend unavailable",
        status: backendRes.status,
        details: errorText,
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }

  // Convert SSE from Python backend to AI SDK UI Message Stream format
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
