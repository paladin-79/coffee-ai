"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";

export function SuccessModal({
  outcome,
  attempts,
  onClose,
}: {
  outcome: "won" | "lost";
  attempts: number;
  onClose: () => void;
}) {
  const won = outcome === "won";
  const panelRef = useRef<HTMLDivElement>(null);

  // Escape dismisses only when there is something to go back to. A lost
  // session has no transcript worth re-reading, so the modal stays put and
  // the only way on is "Chơi lại từ đầu".
  useEffect(() => {
    panelRef.current?.focus();
    if (!won) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [won, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-enamel/80 p-5 backdrop-blur-sm">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="result-heading"
        tabIndex={-1}
        className={`relative w-full max-w-md overflow-hidden rounded-xl border bg-enamel-raised outline-none ${
          won ? "border-caramel" : "border-enamel-edge"
        }`}
      >
        {won && (
          <div
            className="animate-pour absolute inset-x-0 top-0 h-1.5 bg-caramel"
            aria-hidden
          />
        )}

        <div className="p-7">
          <h2
            id="result-heading"
            className={`type-display text-hero ${won ? "text-caramel" : "text-milk"}`}
          >
            {won ? "Bạn đã thắng" : "Hết lượt"}
          </h2>

          <p className="mt-3 text-base text-milk-dim">
            {won
              ? `AI đã gợi ý cà phê sữa đá sau ${attempts} lượt thử.`
              : `Bạn đã dùng hết ${attempts} lượt. Thử lại với một phiên mới nhé.`}
          </p>

          <div className="mt-7 flex flex-col gap-2">
            <Link
              href="/"
              className="type-display rounded-lg bg-caramel px-5 py-3 text-center text-base text-enamel transition-colors hover:bg-caramel-lift"
            >
              Chơi lại từ đầu
            </Link>
            {won && (
              <button
                onClick={onClose}
                className="rounded-lg px-5 py-3 text-small text-milk-dim transition-colors hover:text-milk"
              >
                Xem lại cuộc trò chuyện
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
