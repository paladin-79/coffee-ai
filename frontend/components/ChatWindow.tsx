"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MessageBubble, type ChatMessage } from "./MessageBubble";

/**
 * A picture is shown on the AI turn where the recommendation *changes* — the
 * first time the AI lands on a drink, and again when it flips. Repeating the
 * same photograph on all thirty attempts would say nothing and cost the player
 * on event wifi a scroll full of images.
 */
function imageFlags(messages: ChatMessage[]): boolean[] {
  let previous: string | null = null;
  return messages.map((m) => {
    if (m.role !== "ai" || !m.recommendation) return false;
    const changed = m.recommendation !== previous;
    previous = m.recommendation;
    return changed;
  });
}

export function ChatWindow({
  messages,
  onSend,
  busy,
  disabled,
  decoys = [],
}: {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  busy: boolean;
  disabled: boolean;
  /**
   * Bait, straight from `public.decoy_prompts`. Every one of these trips a
   * guardrail — that is the point. Tapping one only fills the composer; the
   * player still has to press Gửi, so nobody burns an attempt by brushing the
   * screen. They disappear once the player has said anything of their own.
   */
  decoys?: string[];
}) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const flags = useMemo(() => imageFlags(messages), [messages]);
  const started = messages.some((m) => m.role === "user");
  const showDecoys = decoys.length > 0 && !started && !disabled;

  useEffect(() => {
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    endRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
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
      {/* The scroll container stays full-bleed and the measure is applied
          inside it, so the transcript sits on the same axis as the header,
          the state line and the composer. `min-h-full` + `justify-end` keeps a
          short conversation resting on the composer instead of stranding it at
          the top of a projected screen, and still scrolls correctly once the
          transcript outgrows the viewport. */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-end gap-3 px-4 py-5 lg:px-6">
          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} showImage={flags[i]} />
          ))}
          {busy && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-md border border-enamel-edge px-4 py-3 text-base text-milk-dim">
                đang pha…
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {showDecoys && (
        <div className="border-t border-enamel-edge bg-enamel px-4 pt-3 lg:px-6">
          <div className="mx-auto w-full max-w-3xl">
            <p className="text-micro text-milk-dim">Gợi ý</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {decoys.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDraft(d)}
                  className="rounded-full border border-enamel-edge bg-enamel-raised px-3.5 py-3 text-left text-small text-milk-dim transition-colors hover:border-caramel hover:text-milk"
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <form
        onSubmit={submit}
        className="border-t border-enamel-edge bg-enamel-raised px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:px-6"
      >
        <div className="mx-auto flex w-full max-w-3xl gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              disabled ? "Phiên đã kết thúc" : "Nhập câu hỏi của bạn…"
            }
            disabled={busy || disabled}
            // 17px, not 14px: below 16px iOS Safari zooms the whole page on focus.
            className="flex-1 rounded-lg border border-enamel-edge bg-enamel px-4 py-3 text-base text-milk outline-none placeholder:text-milk-dim/60 focus:border-caramel disabled:opacity-50"
            maxLength={2000}
          />
          <button
            type="submit"
            disabled={busy || disabled || !draft.trim()}
            className="type-display rounded-lg bg-caramel px-5 py-3 text-base text-enamel transition-colors hover:bg-caramel-lift disabled:cursor-not-allowed disabled:opacity-40"
          >
            Gửi
          </button>
        </div>
      </form>
    </div>
  );
}
