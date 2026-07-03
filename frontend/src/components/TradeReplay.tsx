import { useState } from "react";
import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";
import { Trade } from "../types";

export default function TradeReplay() {
  const [expanded, setExpanded] = useState(false);
  const { data: trades } = usePolling<Trade[]>("/api/trades", 3000);

  const recentTrades = trades ? [...trades].reverse().slice(0, 10) : [];

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-700/50 transition-colors"
      >
        <span className="font-medium uppercase tracking-wide">Trade Replay (Last 10)</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="p-3 space-y-2 max-h-64 overflow-y-auto">
          {recentTrades.length === 0 ? (
            <p className="text-gray-500 text-xs">No trades yet</p>
          ) : (
            recentTrades.map((trade) => (
              <div
                key={trade.id}
                className={`rounded-lg p-2.5 bg-gray-700/50 border-l-4 ${
                  trade.direction === "BUY" ? "border-green-500" : "border-red-500"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-bold ${
                        trade.direction === "BUY" ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {trade.direction}
                    </span>
                    <span className="text-sm font-medium text-white">{trade.symbol}</span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {formatTime(trade.timestamp)}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-gray-400">
                    {trade.qty} × {formatCurrency(trade.price)}
                  </span>
                  <span className="text-xs text-gray-500">
                    {trade.strategy || "manual"}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}
