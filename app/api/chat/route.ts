import { NextRequest } from "next/server";
import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { randomUUID } from "crypto";

const BACKEND_URL = (process.env.BACKEND_URL ?? "").replace(/\/$/, "");

async function* streamFromBackend(
  messages: unknown[],
  response_time_ms: number | null,
  pdf_url: string | null
): AsyncGenerator<string> {
  const res = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, user_id: "dev-user-1", response_time_ms, pdf_url }),
  });

  if (!res.ok || !res.body) {
    yield `[ERROR] backend returned ${res.status}`;
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value, { stream: true });
    for (const line of text.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data.includes("[DONE]")) break;
      yield data.replace(/\\n/g, "\n");
    }
  }
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { messages, response_time_ms = null, pdf_url = null } = body;
  const lastText = messages?.at(-1)?.parts?.[0]?.text ?? "";

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const id = randomUUID();
      writer.write({ type: "text-start", id });

      if (BACKEND_URL) {
        for await (const chunk of streamFromBackend(messages, response_time_ms, pdf_url)) {
          writer.write({ type: "text-delta", id, delta: chunk });
        }
      } else {
        writer.write({
          type: "text-delta",
          id,
          delta: `[stub] "${lastText}" — configurá BACKEND_URL para conectar con Railway.`,
        });
      }

      writer.write({ type: "text-end", id });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
