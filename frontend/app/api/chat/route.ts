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

  const backendRes = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok || !backendRes.body) {
    return new Response("Backend unavailable", { status: 502 });
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
