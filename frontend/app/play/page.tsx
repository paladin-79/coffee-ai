"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  ApiError,
  type ChallengePublic,
  type SessionStatus,
} from "@/lib/api";
import { splitInstructions } from "@/lib/instructions";
import { ChatWindow } from "@/components/ChatWindow";
import { RecommendationState } from "@/components/RecommendationState";
import { SuccessModal } from "@/components/SuccessModal";
import type { ChatMessage } from "@/components/MessageBubble";

interface StoredSession {
  session_id: string;
  player_id: string;
  max_attempts: number;
  attempts_remaining: number;
  status: SessionStatus;
  /** last enum the model returned; null until the first readable reply */
  recommendation?: string | null;
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
  const [challenge, setChallenge] = useState<ChallengePublic | null>(null);
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
    setSession(s);
    setMessages(loadMessages());
    setShowModal(s.status !== "active");
    ready.current = true;
  }, [router]);

  // The opening line is the mission as challenge.yaml states it — fetched, not
  // hardcoded, so it can never drift from the rules the backend is scoring.
  useEffect(() => {
    api
      .getChallenge()
      .then(setChallenge)
      .catch(() => {
        /* the transcript simply opens empty; the game still works */
      });
  }, []);

  useEffect(() => {
    if (!ready.current || !challenge) return;
    setMessages((m) =>
      m.length
        ? m
        : [
            {
              role: "system",
              text: splitInstructions(challenge.instructions_vi).mission,
            },
          ],
    );
  }, [challenge]);

  // Persist transcript.
  useEffect(() => {
    if (ready.current && messages.length) {
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
            // A blocked prompt never reached the model, so it is not an AI turn.
            role: res.blocked ? "blocked" : "ai",
            text: res.reply,
            recommendation: res.recommendation,
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
          // A block returns null because no model ran — keep the last known
          // position rather than blanking the board.
          recommendation: res.recommendation ?? session.recommendation ?? null,
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
      <main className="flex min-h-screen items-center justify-center text-small text-milk-dim">
        Đang tải…
      </main>
    );
  }

  const finished = session.status !== "active";
  const attemptsUsed = session.max_attempts - session.attempts_remaining;

  return (
    <main className="flex h-[100dvh] flex-col">
      <header className="border-b border-enamel-edge bg-enamel-raised">
        <div className="mx-auto flex w-full max-w-3xl items-center px-4 py-3 lg:px-6">
          <Link
            href="/"
            className="-my-3 py-3 text-small text-milk-dim underline-offset-4 transition-colors hover:text-milk hover:underline"
          >
            ← Thoát
          </Link>
        </div>
      </header>

      <RecommendationState
        recommendation={session.recommendation ?? null}
        won={session.status === "won"}
      />

      <div className="flex-1 overflow-hidden">
        <ChatWindow
          messages={messages}
          onSend={send}
          busy={busy}
          disabled={finished}
          decoys={challenge?.decoy_prompts ?? []}
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
