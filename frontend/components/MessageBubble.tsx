export type Role = "user" | "ai" | "system";

export interface ChatMessage {
  role: Role;
  text: string;
  /** set on the AI turn that won or lost */
  outcome?: "won" | "lost";
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "system") {
    return (
      <div className="mx-auto max-w-md rounded-md bg-amber-100 px-3 py-2 text-center text-sm text-amber-900">
        {message.text}
      </div>
    );
  }

  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={[
          "max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm leading-relaxed",
          isUser
            ? "rounded-br-sm bg-coffee-accent text-white"
            : "rounded-bl-sm bg-white text-coffee-ink shadow-sm",
        ].join(" ")}
      >
        {message.text}
      </div>
    </div>
  );
}
