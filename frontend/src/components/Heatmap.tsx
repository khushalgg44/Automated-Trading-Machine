import { useState, useEffect, useRef } from "react";
import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";
import { Prices } from "../types";

export default function Heatmap() {
  const { data: prices } = usePolling<Prices>("/api/prices", 2000);
  const [sessionStartPrices, setSessionStartPrices] = useState<Prices>({});
  const initialized = useRef(false);

  // Capture session start prices on first data load
  useEffect(() => {
    if (prices && !initialized.current) {
      const symbols = Object.keys(prices);
      if (symbols.length > 0) {
        setSessionStartPrices({ ...prices });
        initialized.current = true;
      }
    }
  }, [prices]);

  if (!prices) return null;

  const symbols = Object.keys(prices);
  if (symbols.length === 0) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
        Market Heatmap
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {symbols.map((symbol) => {
          const currentPrice = prices[symbol];
          const startPrice = sessionStartPrices[symbol] || currentPrice;
          const change = startPrice > 0 ? ((currentPrice - startPrice) / startPrice) * 100 : 0;
          const isPositive = change >= 0;

          // Intensity based on magnitude (0-5% maps to low-high intensity)
          const magnitude = Math.min(Math.abs(change), 5);
          const intensity = Math.round((magnitude / 5) * 100);

          const bgColor = isPositive
            ? `rgba(34, 197, 94, ${0.15 + (intensity / 100) * 0.6})`
            : `rgba(239, 68, 68, ${0.15 + (intensity / 100) * 0.6})`;

          return (
            <div
              key={symbol}
              className="rounded-lg p-3 text-center transition-colors duration-500"
              style={{ backgroundColor: bgColor }}
            >
              <p className="text-xs font-bold text-white">{symbol}</p>
              <p className="text-sm font-mono text-gray-200 mt-0.5">
                {formatCurrency(currentPrice)}
              </p>
              <p
                className={`text-xs font-mono mt-0.5 ${
                  isPositive ? "text-green-300" : "text-red-300"
                }`}
              >
                {isPositive ? "+" : ""}
                {change.toFixed(2)}%
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
