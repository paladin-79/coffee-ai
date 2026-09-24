"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { api, ApiError, type ChallengePublic } from "@/lib/api";
import { splitInstructions } from "@/lib/instructions";

export default function LandingPage() {
  const router = useRouter();
  const [challenge, setChallenge] = useState<ChallengePublic | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");
  const [starting, setStarting] = useState(false);

  const load = useCallback(() => {
    setError(null);
    api
      .getChallenge()
      .then(setChallenge)
      .catch((e: unknown) =>
        setError(
          e instanceof ApiError ? e.message : "Không tải được thử thách.",
        ),
      );
  }, []);

  useEffect(() => {
    load();
    try {
      setNickname(localStorage.getItem("coffee.nickname") ?? "");
    } catch {
      /* private mode */
    }
  }, [load]);

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

  const vi = challenge ? splitInstructions(challenge.instructions_vi) : null;
  const en = challenge ? splitInstructions(challenge.instructions_en) : null;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-5 py-8 lg:px-10 lg:py-12">
      {/* Both the flex column and the grid tracks need an explicit zero min
          size, or the mission line widens the column instead of wrapping. */}
      <div className="flex min-w-0 flex-col gap-8 lg:grid lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:items-center lg:gap-14">
        {/* The illustration is drawn in a warm cream palette that does not
            blend into the enamel ground, so it is matted and framed instead —
            read as a poster pinned to the wall rather than a failed blend.
            It carries the wordmark itself, which is why no separate one is
            drawn on this page. */}
        <figure className="rounded-xl border border-enamel-edge bg-enamel-raised p-2">
          <Image
            src="/image/add-landingpage.png"
            alt="Coffee AI Challenge — một robot và một ly cà phê đứng cạnh bảng gợi ý của AI"
            width={1672}
            height={940}
            priority
            sizes="(max-width: 1024px) 92vw, 520px"
            className="w-full rounded-lg"
          />
        </figure>

        <section className="min-w-0">
          {vi?.setup && (
            <p className="max-w-measure text-small text-milk-dim">{vi.setup}</p>
          )}

          {/* text-balance evens out the line lengths instead of leaving one
              orphaned word on the last line, which is what made the ragged
              right edge look accidental at this size. */}
          <h1 className="type-display type-mission mt-3 text-balance break-words text-milk">
            {vi?.mission ?? "Đang tải thử thách…"}
          </h1>

          {en && (
            <p
              lang="en"
              className="mt-6 max-w-measure border-l-2 border-enamel-edge pl-4 text-small text-milk-dim"
            >
              {en.setup ? `${en.setup} ` : ""}
              {en.mission}
            </p>
          )}

          <div className="mt-7 max-w-sm">
            <label className="block">
              <span className="text-small font-medium text-milk">
                Biệt danh{" "}
                <span className="font-normal text-milk-dim">(tuỳ chọn)</span>
              </span>
              <input
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                maxLength={40}
                placeholder="cà phê thủ"
                disabled={starting}
                className="mt-2 w-full rounded-lg border border-enamel-edge bg-enamel-raised px-4 py-3 text-base text-milk outline-none placeholder:text-milk-dim/60 focus:border-caramel disabled:opacity-50"
              />
            </label>

            <button
              onClick={start}
              disabled={starting || !challenge}
              className="type-display mt-3 w-full rounded-lg bg-caramel px-6 py-4 text-lead text-enamel transition-colors hover:bg-caramel-lift disabled:cursor-not-allowed disabled:opacity-40"
            >
              {starting ? "Đang bắt đầu…" : "Bắt đầu"}
            </button>

            {error && (
              <div className="mt-5 rounded-lg border border-signal bg-signal-wash p-4">
                <p className="text-small text-signal-bright">{error}</p>
                {!challenge && (
                  <button
                    onClick={load}
                    className="mt-3 rounded-md border border-signal px-4 py-2 text-small font-medium text-milk hover:bg-signal/20"
                  >
                    Thử lại
                  </button>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
