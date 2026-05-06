import { NextRequest } from "next/server";
import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { randomUUID } from "crypto";

const BACKEND_URL = process.env.BACKEND_URL;

async function* streamFromBackend(messages: unknown[]): AsyncGenerator<string> {
  const res = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, user_id: "anonymous" }),
  });

  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value, { stream: true });
    for (const line of text.split("\n")) {
      if (line.startsWith("data: ") && !line.includes("[DONE]")) {
        yield line.slice(6).replace(/\\n/g, "\n");
      }
    }
  }
}

export async function POST(req: NextRequest) {
  const { messages } = await req.json();
  const lastText = messages?.at(-1)?.parts?.[0]?.text ?? "";

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const id = randomUUID();
      writer.write({ type: "text-start", id });

      if (BACKEND_URL) {
        for await (const chunk of streamFromBackend(messages)) {
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
