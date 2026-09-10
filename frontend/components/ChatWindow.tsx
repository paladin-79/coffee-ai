"use client";

import { useEffect, useRef, useState } from "react";
import { MessageBubble, type ChatMessage } from "./MessageBubble";

export function ChatWindow({
  messages,
  onSend,
  busy,
  disabled,
}: {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  busy: boolean;
  disabled: boolean;
}) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy || disabled) return;
    setDraft("");
    onSend(text);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-2 text-sm text-stone-400 shadow-sm">
              đang pha…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="border-t border-stone-200 bg-white p-3">
        <div className="flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              disabled ? "Phiên đã kết thúc" : "Nhập câu hỏi của bạn…"
            }
            disabled={busy || disabled}
            className="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm outline-none focus:border-coffee-accent disabled:bg-stone-100"
            maxLength={2000}
          />
          <button
            type="submit"
            disabled={busy || disabled || !draft.trim()}
            className="rounded-lg bg-coffee-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            Gửi
          </button>
        </div>
      </form>
    </div>
  );
}
