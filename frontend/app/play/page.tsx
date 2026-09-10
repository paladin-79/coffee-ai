"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, type SessionStatus } from "@/lib/api";
import { ChatWindow } from "@/components/ChatWindow";
import { AttemptCounter } from "@/components/AttemptCounter";
import { SuccessModal } from "@/components/SuccessModal";
import type { ChatMessage } from "@/components/MessageBubble";

interface StoredSession {
  session_id: string;
  player_id: string;
  max_attempts: number;
  attempts_remaining: number;
  status: SessionStatus;
}

function loadSession(): StoredSession | null {
  try {
    const raw = localStorage.getItem("coffee.session");
    return raw ? (JSON.parse(raw) as StoredSession) : null;
  } catch {
    return null;
  }
}

function loadMessages(): ChatMessage[] {
  try {
    const raw = localStorage.getItem("coffee.messages");
    return raw ? (JSON.parse(raw) as ChatMessage[]) : [];
  } catch {
    return [];
  }
}

export default function PlayPage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const ready = useRef(false);

  // Restore or bounce to the landing page.
  useEffect(() => {
    const s = loadSession();
    if (!s) {
      router.replace("/");
      return;
    }
    const restored = loadMessages();
    setSession(s);
    setMessages(
      restored.length
        ? restored
        : [
            {
              role: "system",
              text: "Hãy khiến trợ lý gợi ý cà phê sữa đá — nhưng đừng hỏi thẳng.",
            },
          ],
    );
    setShowModal(s.status !== "active");
    ready.current = true;
  }, [router]);

  // Persist transcript.
  useEffect(() => {
    if (ready.current) {
      try {
        localStorage.setItem("coffee.messages", JSON.stringify(messages));
      } catch {
        /* ignore */
      }
    }
  }, [messages]);

  const persistSession = useCallback((next: StoredSession) => {
    setSession(next);
    try {
      localStorage.setItem("coffee.session", JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (!session) return;
      setMessages((m) => [...m, { role: "user", text }]);
      setBusy(true);
      try {
        const res = await api.chat(session.session_id, text);
        setMessages((m) => [
          ...m,
          {
            role: "ai",
            text: res.reply,
            outcome: res.success
              ? "won"
              : res.status === "lost"
                ? "lost"
                : undefined,
          },
        ]);
        persistSession({
          ...session,
          attempts_remaining: res.attempts_remaining,
          status: res.status,
        });
        if (res.status !== "active") setShowModal(true);
      } catch (e: unknown) {
        if (e instanceof ApiError && e.status === 503) {
          setMessages((m) => [
            ...m,
            {
              role: "system",
              text: "AI đang bận, lượt này không bị tính. Thử lại nhé.",
            },
          ]);
        } else if (e instanceof ApiError && e.status === 404) {
          localStorage.removeItem("coffee.session");
          localStorage.removeItem("coffee.messages");
          router.replace("/");
        } else if (e instanceof ApiError && e.status === 409) {
          persistSession({ ...session, status: "lost" });
          setShowModal(true);
        } else {
          setMessages((m) => [
            ...m,
            {
              role: "system",
              text:
                e instanceof ApiError ? e.message : "Có lỗi xảy ra. Thử lại.",
            },
          ]);
        }
      } finally {
        setBusy(false);
      }
    },
    [session, persistSession, router],
  );

  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-stone-500">
        Đang tải…
      </main>
    );
  }

  const finished = session.status !== "active";
  const attemptsUsed = session.max_attempts - session.attempts_remaining;

  return (
    <main className="mx-auto flex h-screen max-w-xl flex-col">
      <header className="flex items-center justify-between border-b border-stone-200 bg-white px-4 py-3">
        <Link href="/" className="text-sm text-stone-500 hover:text-stone-800">
          ← Thoát
        </Link>
        <AttemptCounter
          remaining={session.attempts_remaining}
          max={session.max_attempts}
        />
      </header>

      <div className="flex-1 overflow-hidden">
        <ChatWindow
          messages={messages}
          onSend={send}
          busy={busy}
          disabled={finished}
        />
      </div>

      {showModal && finished && (
        <SuccessModal
          outcome={session.status === "won" ? "won" : "lost"}
          attempts={attemptsUsed}
          onClose={() => setShowModal(false)}
        />
      )}
    </main>
  );
}
