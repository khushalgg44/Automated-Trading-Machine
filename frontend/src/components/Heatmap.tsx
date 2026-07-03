import { useState, useEffect, useRef } from "react";
import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";
import { Prices } from "../types";

export default function Heatmap() {
  const { data: prices } = usePolling<Prices>("/api/prices", 2000);
  const { data: universe } = usePolling<string[]>("/api/universe", 30000);
  const [sessionStartPrices, setSessionStartPrices] = useState<Prices>({});
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const initialized = useRef(false);

  // Capture session start prices on first data load
  useEffect(() => {
    if (prices && !initialized.current) {
      const symbols = Object.keys(prices);
      if (symbols.length > 0) {
        setSessionStartPrices({ ...prices });
        setSelectedSymbols(symbols);
        initialized.current = true;
      }
    }
  }, [prices]);

  if (!prices) return null;

  const allSymbols = Object.keys(prices);
  const displaySymbols = selectedSymbols.length > 0 ? selectedSymbols.filter(s => prices[s] !== undefined) : allSymbols;
  const available = allSymbols.filter(s => !displaySymbols.includes(s));

  const addSymbol = (sym: string) => {
    setSelectedSymbols([...displaySymbols, sym]);
    setShowAdd(false);
  };

  const removeSymbol = (sym: string) => {
    setSelectedSymbols(displaySymbols.filter(s => s !== sym));
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
          {showAdd && available.length > 0 && (
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {displaySymbols.map((symbol) => {
          const currentPrice = prices[symbol];
          if (!currentPrice) return null;
          const startPrice = sessionStartPrices[symbol] || currentPrice;
          const change = startPrice > 0 ? ((currentPrice - startPrice) / startPrice) * 100 : 0;
          const isPositive = change >= 0;
          const magnitude = Math.min(Math.abs(change), 5);
          const intensity = Math.round((magnitude / 5) * 100);
          const bgColor = isPositive
            ? `rgba(34, 197, 94, ${0.15 + (intensity / 100) * 0.6})`
            : `rgba(239, 68, 68, ${0.15 + (intensity / 100) * 0.6})`;

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
                {formatCurrency(currentPrice)}
              </p>
              <p className={`text-xs font-mono mt-0.5 ${isPositive ? "text-green-300" : "text-red-300"}`}>
                {isPositive ? "+" : ""}{change.toFixed(2)}%
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
