import { drinkFor } from "@/lib/drinks";

// The scoreboard of the game. The backend already returns `recommendation` on
// every attempt (the enum the challenge engine actually scores, not the prose);
// before this it was discarded and players had to infer the AI's position by
// reading its reply.
//
// On a blocked attempt the model never ran and the backend sends null, so the
// last known position is kept rather than cleared — that is what is true.

export function RecommendationState({
  recommendation,
  won,
}: {
  recommendation: string | null;
  won: boolean;
}) {
  const drink = drinkFor(recommendation);

  // Nothing to report until the AI has actually landed somewhere. An empty
  // scoreboard with a placeholder line was just noise at the top of the
  // screen, so the whole strip stays out of the way until it has news.
  if (!drink) return null;

  return (
    <div className="border-b border-enamel-edge bg-enamel">
      <div className="mx-auto w-full max-w-3xl px-4 py-3 lg:px-6">
        <p className="text-micro text-milk-dim">AI đang gợi ý</p>
        {/* This is what the room reads from across the table, so it steps up
            with the viewport rather than staying at chat scale. */}
        <p
          className={`type-display mt-0.5 text-title lg:text-hero ${
            won ? "text-caramel" : "text-milk"
          }`}
        >
          {drink.label}
        </p>
      </div>
    </div>
  );
}
