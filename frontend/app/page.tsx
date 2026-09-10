"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, type ChallengePublic } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [challenge, setChallenge] = useState<ChallengePublic | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    api
      .getChallenge()
      .then(setChallenge)
      .catch((e: unknown) =>
        setError(e instanceof ApiError ? e.message : "Không tải được thử thách."),
      );
    try {
      setNickname(localStorage.getItem("coffee.nickname") ?? "");
    } catch {
      /* private mode */
    }
  }, []);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const session = await api.createSession(nickname);
      localStorage.setItem("coffee.nickname", nickname.trim());
      localStorage.setItem(
        "coffee.session",
        JSON.stringify({
          session_id: session.session_id,
          player_id: session.player_id,
          max_attempts: session.max_attempts,
          attempts_remaining: session.attempts_remaining,
          status: "active",
        }),
      );
      localStorage.removeItem("coffee.messages");
      router.push("/play");
    } catch (e: unknown) {
      setError(
        e instanceof ApiError ? e.message : "Không tạo được phiên chơi.",
      );
      setStarting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-5 py-10">
      <div className="text-5xl">☕</div>
      <h1 className="mt-4 text-3xl font-bold">
        {challenge?.title ?? "Coffee AI Challenge"}
      </h1>
      <p className="mt-2 text-lg text-stone-600">
        {challenge?.tagline ?? "…"}
      </p>

      {challenge && (
        <div className="mt-6 space-y-3 rounded-xl bg-white p-4 text-sm leading-relaxed shadow-sm">
          <p className="whitespace-pre-line">{challenge.instructions_vi}</p>
          <p className="whitespace-pre-line text-stone-500">
            {challenge.instructions_en}
          </p>
          <p className="text-stone-500">
            Bạn có <strong>{challenge.max_attempts}</strong> lượt thử.
          </p>
        </div>
      )}

      <label className="mt-6 block text-sm font-medium">
        Biệt danh <span className="text-stone-400">(tuỳ chọn)</span>
        <input
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          maxLength={40}
          placeholder="cà phê thủ"
          className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 outline-none focus:border-coffee-accent"
        />
      </label>

      <button
        onClick={start}
        disabled={starting || !challenge}
        className="mt-4 rounded-xl bg-coffee-accent px-5 py-3 text-base font-semibold text-white disabled:opacity-40"
      >
        {starting ? "Đang bắt đầu…" : "Bắt đầu"}
      </button>

      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
    </main>
  );
}
