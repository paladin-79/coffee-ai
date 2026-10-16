// Shows the backend's attempts_remaining. Never computed on the client — the
// server owns the count (see frontend/README.md).
//
// With 30 attempts a dotted pip row would be noise, so the count is plain
// numerals: the remaining figure large enough to read from across a room, the
// total demoted beside it.

export function AttemptCounter({
  remaining,
  max,
}: {
  remaining: number;
  max: number;
}) {
  const low = remaining <= Math.max(1, Math.ceil(max * 0.2));
  return (
    <span className="flex items-baseline gap-1.5" title="Số lượt thử còn lại">
      <span
        className={`type-display text-lead tabular-nums lg:text-title ${
          low ? "text-signal-bright" : "text-milk"
        }`}
      >
        {remaining}
      </span>
      <span className="text-micro tabular-nums text-milk-dim lg:text-small">
        / {max} lượt
      </span>
    </span>
  );
}
