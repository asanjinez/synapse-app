"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { upload } from "@vercel/blob/client";
import { useState, useEffect, useRef } from "react";

const transport = new DefaultChatTransport({ api: "/api/chat" });

export function ChatWindow() {
  const [input, setInput] = useState("");
  const [pendingPdf, setPendingPdf] = useState<{ name: string; url: string } | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const agentRespondedAtRef = useRef<number | null>(null);

  const { messages, sendMessage, status } = useChat({ transport });
  const isLoading = status === "streaming" || status === "submitted";

  useEffect(() => {
    if (status === "ready" && messages.at(-1)?.role === "assistant") {
      agentRespondedAtRef.current = Date.now();
    }
  }, [status, messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const response_time_ms =
      agentRespondedAtRef.current !== null
        ? Date.now() - agentRespondedAtRef.current
        : null;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (sendMessage as any)(
      { text: input },
      { body: { response_time_ms, pdf_url: pendingPdf?.url ?? null } }
    );
    setInput("");
    setPendingPdf(null);
    agentRespondedAtRef.current = null;
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    setUploadStatus("Subiendo a Blob...");
    try {
      const blob = await upload(file.name, file, {
        access: "public",
        handleUploadUrl: "/api/blob/upload",
      });
      setPendingPdf({ name: file.name, url: blob.url });
      setUploadStatus(null);
    } catch {
      setUploadStatus("✗ Error al subir el archivo");
      setTimeout(() => setUploadStatus(null), 3000);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-zinc-950">
      {uploadStatus && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-sm px-4 py-2 rounded-xl shadow-lg">
          {uploadStatus}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-3xl mx-auto w-full">
        {messages.length === 0 && (
          <p className="text-zinc-400 text-center mt-20">
            Hola, soy Synapse. ¿Qué querés aprender hoy?
          </p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
              }`}
            >
              {m.parts?.map((part, i) =>
                part.type === "text" ? <span key={i}>{part.text}</span> : null
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-zinc-100 dark:bg-zinc-800 rounded-2xl px-4 py-3">
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-zinc-200 dark:border-zinc-800 px-4 py-4"
      >
        <div className="max-w-3xl mx-auto flex flex-col gap-2">
          {pendingPdf && (
            <div className="flex items-center gap-2 bg-zinc-100 dark:bg-zinc-800 rounded-xl px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <span className="flex-1 truncate">{pendingPdf.name}</span>
              <button
                type="button"
                onClick={() => setPendingPdf(null)}
                className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-100"
              >
                ✕
              </button>
            </div>
          )}
          <div className="flex gap-2 items-center">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              title="Adjuntar PDF"
              disabled={isLoading}
              className="rounded-xl border border-zinc-200 dark:border-zinc-700 px-3 py-3 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors disabled:opacity-40"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="12" y1="18" x2="12" y2="12"/>
                <line x1="9" y1="15" x2="15" y2="15"/>
              </svg>
            </button>

            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              placeholder={pendingPdf ? `Adjuntado: ${pendingPdf.name}. Escribí tu mensaje...` : "Escribí tu mensaje..."}
              className="flex-1 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-zinc-300 dark:focus:ring-zinc-600 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-5 py-3 text-sm font-medium disabled:opacity-40 transition-opacity"
            >
              Enviar
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
