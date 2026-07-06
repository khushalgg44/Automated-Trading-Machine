import { useState, useEffect, useRef } from "react";
import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";
import { Prices } from "../types";

export default function Heatmap() {
  const { data: prices } = usePolling<Prices>("/api/prices", 2000);
  const { data: universe } = usePolling<string[]>("/api/universe", 30000);
  const [sessionStartPrices, setSessionStartPrices] = useState<Prices>({});
  const [displaySymbols, setDisplaySymbols] = useState<string[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [customInput, setCustomInput] = useState("");
  const initialized = useRef(false);

  useEffect(() => {
    if (prices && !initialized.current) {
      const symbols = Object.keys(prices);
      if (symbols.length > 0) {
        setSessionStartPrices({ ...prices });
        setDisplaySymbols(symbols);
        initialized.current = true;
      }
    }
    // Also capture start price for newly added symbols
    if (prices && initialized.current) {
      for (const sym of displaySymbols) {
        if (prices[sym] && !sessionStartPrices[sym]) {
          setSessionStartPrices(prev => ({ ...prev, [sym]: prices[sym] }));
        }
      }
    }
  }, [prices, displaySymbols]);

  if (!prices) return null;

  const available = (universe || []).filter(s => !displaySymbols.includes(s));

  const addSymbol = (sym: string) => {
    const upper = sym.toUpperCase().trim();
    if (upper && !displaySymbols.includes(upper)) {
      setDisplaySymbols(prev => [...prev, upper]);
    }
    setShowAdd(false);
    setCustomInput("");
  };

  const removeSymbol = (sym: string) => {
    setDisplaySymbols(prev => prev.filter(s => s !== sym));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customInput.trim()) addSymbol(customInput);
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          Market Heatmap
        </h2>
        <div className="relative">
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300 hover:bg-gray-600 font-bold"
          >
            + Add
          </button>
          {showAdd && (
            <div className="absolute right-0 top-7 z-50 bg-gray-900 border border-gray-700 rounded shadow-2xl p-2 min-w-[180px]"
              onClick={(e) => e.stopPropagation()}>
              <form onSubmit={handleSubmit} className="flex gap-1 mb-2">
                <input
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value)}
                  placeholder="Type symbol..."
                  autoFocus
                  className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-blue-500"
                />
                <button type="submit" className="px-2 py-1 bg-green-600 rounded text-xs text-white font-bold">Add</button>
              </form>
              {available.length > 0 && (
                <div className="max-h-32 overflow-y-auto">
                  {available.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={(e) => { e.stopPropagation(); addSymbol(s); }}
                      className="block w-full text-left px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 hover:text-white rounded cursor-pointer"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {displaySymbols.map((symbol) => {
          const currentPrice = prices[symbol];
          const startPrice = sessionStartPrices[symbol] || currentPrice;
          const change = currentPrice && startPrice ? ((currentPrice - startPrice) / startPrice) * 100 : 0;
          const isPositive = change >= 0;
          const magnitude = Math.min(Math.abs(change), 5);
          const intensity = Math.round((magnitude / 5) * 100);
          const bgColor = currentPrice
            ? isPositive
              ? `rgba(34, 197, 94, ${0.15 + (intensity / 100) * 0.6})`
              : `rgba(239, 68, 68, ${0.15 + (intensity / 100) * 0.6})`
            : "rgba(107, 114, 128, 0.2)";

          return (
            <div
              key={symbol}
              className="rounded-lg p-3 text-center transition-colors duration-500 relative group"
              style={{ backgroundColor: bgColor }}
            >
              <button
                onClick={() => removeSymbol(symbol)}
                className="absolute top-1 right-1 text-gray-500 hover:text-red-400 text-xs opacity-0 group-hover:opacity-100"
              >
                ×
              </button>
              <p className="text-xs font-bold text-white">{symbol}</p>
              <p className="text-sm font-mono text-gray-200 mt-0.5">
                {currentPrice ? formatCurrency(currentPrice) : "—"}
              </p>
              <p className={`text-xs font-mono mt-0.5 ${isPositive ? "text-green-300" : "text-red-300"}`}>
                {currentPrice ? `${isPositive ? "+" : ""}${change.toFixed(2)}%` : "No data"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
