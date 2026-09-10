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
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 text-center shadow-xl">
        <div className="text-4xl">{won ? "🎉" : "☕"}</div>
        <h2 className="mt-3 text-xl font-semibold">
          {won ? "Bạn đã thắng!" : "Hết lượt rồi"}
        </h2>
        <p className="mt-2 text-sm text-stone-600">
          {won
            ? `AI đã gợi ý cà phê sữa đá sau ${attempts} lượt thử.`
            : `Bạn đã dùng hết ${attempts} lượt. Thử lại với một phiên mới nhé.`}
        </p>
        <div className="mt-5 flex flex-col gap-2">
          <Link
            href="/"
            className="rounded-lg bg-coffee-accent px-4 py-2 text-sm font-medium text-white"
          >
            Chơi lại từ đầu
          </Link>
          {won && (
            <button
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm text-stone-500 hover:text-stone-800"
            >
              Xem lại cuộc trò chuyện
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
