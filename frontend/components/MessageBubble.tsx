import Image from "next/image";
import { drinkFor } from "@/lib/drinks";

export type Role = "user" | "ai" | "system" | "blocked";

export interface ChatMessage {
  role: Role;
  text: string;
  /** set on the AI turn that won or lost */
  outcome?: "won" | "lost";
  /** the enum this AI turn recommended; null on a blocked or unreadable turn */
  recommendation?: string | null;
}

/**
 * Four voices, four structures — filled, outlined, stamped, bare. The
 * distinction is carried by shape rather than colour alone, so it survives a
 * projector, a phone in sunlight, and colour-blind players.
 *
 * A guardrail block is deliberately styled apart from the AI's own replies:
 * the assistant did not say this, and the attempt still counted. Which
 * guardrail fired is never sent to the browser.
 */
export function MessageBubble({
  message,
  showImage = false,
}: {
  message: ChatMessage;
  showImage?: boolean;
}) {
  if (message.role === "blocked") {
    return (
      <div className="animate-settle flex justify-center">
        <div className="max-w-measure rounded-lg border-2 border-signal p-[3px]">
          <div className="rounded-md border border-signal/40 bg-signal-wash px-4 py-3">
            <p className="whitespace-pre-wrap text-center text-small text-signal-bright">
              {message.text}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (message.role === "system") {
    return (
      <div className="animate-settle flex justify-center px-4 py-1">
        <p className="max-w-measure text-center text-small text-milk-dim">
          {message.text}
        </p>
      </div>
    );
  }

  const isUser = message.role === "user";
  const won = message.role === "ai" && message.outcome === "won";
  const drink =
    message.role === "ai" && showImage
      ? drinkFor(message.recommendation)
      : null;
  const picture = drink?.image ? drink : null;

  if (isUser) {
    return (
      <div className="animate-settle flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-milk px-4 py-3 text-base text-enamel">
          {message.text}
        </p>
      </div>
    );
  }

  // The win is the one bold moment in the app, so the reply that finally
  // flipped the recommendation is filled solid rather than tinted — a caramel
  // wash over the enamel ground turns olive and reads as the drabbest thing on
  // screen, which is the opposite of what this moment is for.
  return (
    <div className="animate-settle flex justify-start">
      <div
        className={`max-w-[85%] overflow-hidden rounded-2xl rounded-bl-md ${
          won
            ? "bg-caramel text-enamel"
            : "border border-enamel-edge bg-enamel-raised text-milk"
        }`}
      >
        {picture && (
          <Image
            src={picture.image}
            alt={picture.alt}
            width={picture.width}
            height={picture.height}
            sizes="(max-width: 768px) 85vw, 640px"
            className="aspect-[16/9] w-full object-cover"
          />
        )}
        <p
          className={`whitespace-pre-wrap px-4 py-3 text-base ${
            won ? "font-medium" : ""
          }`}
        >
          {message.text}
        </p>
      </div>
    </div>
  );
}
