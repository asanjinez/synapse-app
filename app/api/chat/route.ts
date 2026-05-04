import { NextRequest } from "next/server";
import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { randomUUID } from "crypto";

export async function POST(req: NextRequest) {
  // Phase 1 stub — Phase 2: proxy a FastAPI + LangGraph
  const { messages } = await req.json();
  const lastText = messages?.at(-1)?.parts?.[0]?.text ?? "";

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const id = randomUUID();
      writer.write({ type: "text-start", id });
      writer.write({
        type: "text-delta",
        id,
        delta: `[stub] Recibí: "${lastText}". En Phase 2 esto conecta con LangGraph.`,
      });
      writer.write({ type: "text-end", id });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
