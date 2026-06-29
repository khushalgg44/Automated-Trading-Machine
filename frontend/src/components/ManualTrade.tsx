import { useState } from "react";
import { Prices } from "../types";
import { usePolling } from "../hooks/usePolling";

interface Props {
  prices: Prices | null;
}

export default function ManualTrade({ prices }: Props) {
  const { data: watchlistSymbols } = usePolling<string[]>("/api/watchlist", 3000);
  const symbols = watchlistSymbols || (prices ? Object.keys(prices) : []);
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState(10);
  const [status, setStatus] = useState<{
    type: "success" | "error" | null;
    message: string;
  }>({ type: null, message: "" });
  const [submitting, setSubmitting] = useState(false);

  // Auto-select first symbol if none selected
  const selectedSymbol = symbol || symbols[0] || "";

  const handleSubmit = async () => {
    if (!selectedSymbol) return;
    setSubmitting(true);
    setStatus({ type: null, message: "" });

    try {
      const res = await fetch("/api/manual-trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: selectedSymbol, side, quantity }),
      });

      const data = await res.json();

      if (!res.ok) {
        setStatus({ type: "error", message: data.detail || "Request failed" });
      } else if (data.status === "rejected") {
        setStatus({ type: "error", message: data.reason });
      } else {
        const t = data.trade;
        setStatus({
          type: "success",
          message: `${t.direction} ${t.qty}x ${t.symbol} @ ₹${t.price.toFixed(2)}`,
        });
        // Clear success after 3s
        setTimeout(() => setStatus({ type: null, message: "" }), 3000);
      }
    } catch (err: any) {
      setStatus({ type: "error", message: err.message || "Network error" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">
        Manual Trade
      </h2>

      <div className="space-y-3">
        {/* Symbol selector */}
        <div>
          <label className="text-xs text-gray-500 block mb-1">Symbol</label>
          <select
            value={selectedSymbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500"
          >
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* BUY / SELL toggle */}
        <div>
          <label className="text-xs text-gray-500 block mb-1">Side</label>
          <div className="flex gap-1">
            <button
              onClick={() => setSide("BUY")}
              className={`flex-1 py-2 rounded text-sm font-bold transition-colors ${
                side === "BUY"
                  ? "bg-green-600 text-white"
                  : "bg-gray-700 text-gray-400 hover:bg-gray-600"
              }`}
            >
              BUY
            </button>
            <button
              onClick={() => setSide("SELL")}
              className={`flex-1 py-2 rounded text-sm font-bold transition-colors ${
                side === "SELL"
                  ? "bg-red-600 text-white"
                  : "bg-gray-700 text-gray-400 hover:bg-gray-600"
              }`}
            >
              SELL
            </button>
          </div>
        </div>

        {/* Quantity */}
        <div>
          <label className="text-xs text-gray-500 block mb-1">Quantity</label>
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-mono text-white focus:outline-none focus:border-green-500"
          />
        </div>

        {/* Execute button */}
        <button
          onClick={handleSubmit}
          disabled={submitting || !selectedSymbol}
          className={`w-full py-2.5 rounded font-bold text-sm transition-colors ${
            submitting
              ? "bg-gray-700 text-gray-500 cursor-wait"
              : side === "BUY"
              ? "bg-green-600 hover:bg-green-500 text-white"
              : "bg-red-600 hover:bg-red-500 text-white"
          }`}
        >
          {submitting ? "Executing..." : `Execute ${side}`}
        </button>

        {/* Status message */}
        {status.type && (
          <div
            className={`text-sm px-3 py-2 rounded ${
              status.type === "success"
                ? "bg-green-900/40 text-green-400 border border-green-800"
                : "bg-red-900/40 text-red-400 border border-red-800"
            }`}
          >
            {status.message}
          </div>
        )}
      </div>
    </div>
  );
}
