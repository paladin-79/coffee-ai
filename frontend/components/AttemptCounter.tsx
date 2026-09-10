// Shows the backend's attempts_remaining. Never computed on the client — the
// server owns the count (see frontend/README.md).

export function AttemptCounter({
  remaining,
  max,
}: {
  remaining: number;
  max: number;
}) {
  const low = remaining <= Math.max(1, Math.ceil(max * 0.2));
  return (
    <span
      className={[
        "rounded-full px-3 py-1 text-sm font-medium tabular-nums",
        low ? "bg-red-100 text-red-800" : "bg-stone-200 text-stone-700",
      ].join(" ")}
      title="Số lượt thử còn lại"
    >
      {remaining} / {max} lượt
    </span>
  );
}
