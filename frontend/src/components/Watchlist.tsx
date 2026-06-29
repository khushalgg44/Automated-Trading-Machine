import { useState, useEffect } from "react";
import { Prices } from "../types";
import { formatCurrency } from "../utils";
import { usePolling } from "../hooks/usePolling";

interface Props {
  prices: Prices | null;
}

export default function Watchlist({ prices }: Props) {
  const { data: watchlistSymbols } = usePolling<string[]>("/api/watchlist", 3000);
  const { data: universe } = usePolling<string[]>("/api/universe", 30000);
  const [adding, setAdding] = useState(false);
  const [sessionStart] = useState<Prices>({});

  // Track session start prices (first price we see for each symbol)
  useEffect(() => {
    if (!prices) return;
    for (const [sym, price] of Object.entries(prices)) {
      if (!(sym in sessionStart)) {
        sessionStart[sym] = price;
      }
    }
  }, [prices]);

  const addSymbol = async (symbol: string) => {
    try {
      await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol }),
      });
    } catch { /* silent */ }
    setAdding(false);
  };

  const removeSymbol = async (symbol: string) => {
    try {
      await fetch(`/api/watchlist/${symbol}`, { method: "DELETE" });
    } catch { /* silent */ }
  };

  const available = universe?.filter((s) => !watchlistSymbols?.includes(s)) || [];

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          Watchlist
        </h2>
        <div className="relative">
          <button
            onClick={() => setAdding(!adding)}
            className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300 hover:bg-gray-600 font-bold"
          >
            +
          </button>
          {adding && available.length > 0 && (
            <div className="absolute right-0 top-7 z-10 bg-gray-900 border border-gray-700 rounded shadow-lg py-1 min-w-[120px]">
              {available.map((s) => (
                <button
                  key={s}
                  onClick={() => addSymbol(s)}
                  className="block w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700 hover:text-white"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {!watchlistSymbols || watchlistSymbols.length === 0 ? (
        <p className="text-gray-500 text-sm">No symbols in watchlist</p>
      ) : (
        <div className="space-y-1.5">
          {watchlistSymbols.map((sym) => {
            const price = prices?.[sym];
            const startPrice = sessionStart[sym];
            const change = price && startPrice ? ((price - startPrice) / startPrice) * 100 : null;
            const isUp = change !== null && change >= 0;

            return (
              <div
                key={sym}
                className="flex items-center justify-between py-1.5 px-2.5 bg-gray-900/50 rounded group"
              >
                <span className="font-medium text-white text-sm">{sym}</span>
                <div className="flex items-center gap-2">
                  {price ? (
                    <span className={`font-mono text-sm ${isUp ? "text-green-400" : "text-red-400"}`}>
                      {formatCurrency(price)}
                    </span>
                  ) : (
                    <span className="font-mono text-sm text-gray-500">—</span>
                  )}
                  {change !== null && (
                    <span className={`font-mono text-xs ${isUp ? "text-green-500" : "text-red-500"}`}>
                      {isUp ? "+" : ""}{change.toFixed(2)}%
                    </span>
                  )}
                  <button
                    onClick={() => removeSymbol(sym)}
                    className="text-gray-600 hover:text-red-400 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
