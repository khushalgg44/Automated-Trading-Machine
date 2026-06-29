import { useState } from "react";
import { usePolling } from "../hooks/usePolling";
import { Trade } from "../types";
import { formatCurrency } from "../utils";

export default function TradesTable() {
  const { data, error, loading } = usePolling<Trade[]>("/api/trades", 2000);

  const recent = data ? data.slice(-20).reverse() : [];

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          Recent Trades
        </h2>
        <a
          href="/api/export/trades"
          target="_blank"
          className="text-xs text-gray-500 hover:text-white transition-colors"
          title="Export trades CSV"
        >
          📥 Export CSV
        </a>
      </div>
      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : recent.length === 0 ? (
        <p className="text-gray-500 text-sm">No trades yet</p>
      ) : (
        <div className="overflow-x-auto max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-800">
              <tr className="text-gray-500 text-xs uppercase border-b border-gray-700">
                <th className="text-left pb-2">Time</th>
                <th className="text-left pb-2">Symbol</th>
                <th className="text-left pb-2">Side</th>
                <th className="text-right pb-2">Qty</th>
                <th className="text-right pb-2">Price</th>
                <th className="text-right pb-2">P&L</th>
                <th className="text-left pb-2">Strategy</th>
                <th className="text-center pb-2">Note</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TradeRow({ trade }: { trade: Trade }) {
  const [editing, setEditing] = useState(false);
  const [noteText, setNoteText] = useState(trade.note || "");
  const [saving, setSaving] = useState(false);

  const saveNote = async () => {
    setSaving(true);
    try {
      await fetch(`/api/trade/${trade.id}/note`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: noteText }),
      });
    } catch {
      // silent
    } finally {
      setSaving(false);
      setEditing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") saveNote();
    if (e.key === "Escape") setEditing(false);
  };

  return (
    <>
      <tr className="border-b border-gray-700/50 hover:bg-gray-700/30">
        <td className="py-1.5 text-gray-400 font-mono text-xs">
          {formatTime(trade.timestamp)}
        </td>
        <td className="py-1.5 font-medium text-white">{trade.symbol}</td>
        <td className="py-1.5">
          <span
            className={`px-1.5 py-0.5 rounded text-xs font-bold ${
              trade.direction === "BUY"
                ? "bg-green-900/40 text-green-400"
                : "bg-red-900/40 text-red-400"
            }`}
          >
            {trade.direction}
          </span>
        </td>
        <td className="py-1.5 text-right font-mono">{trade.qty}</td>
        <td className="py-1.5 text-right font-mono">{formatCurrency(trade.price)}</td>
        <td
          className={`py-1.5 text-right font-mono text-xs ${
            trade.pnl > 0 ? "text-green-400" : trade.pnl < 0 ? "text-red-400" : "text-gray-500"
          }`}
        >
          {trade.pnl !== 0 ? `${trade.pnl > 0 ? "+" : ""}${formatCurrency(trade.pnl)}` : "—"}
        </td>
        <td className="py-1.5 text-xs text-gray-400">{trade.strategy || "—"}</td>
        <td className="py-1.5 text-center">
          <button
            onClick={() => setEditing(!editing)}
            className={`text-xs px-1 rounded hover:bg-gray-700 ${trade.note ? "text-yellow-400" : "text-gray-600"}`}
            title={trade.note || "Add note"}
          >
            📝
          </button>
        </td>
      </tr>
      {editing && (
        <tr>
          <td colSpan={8} className="py-1 px-2">
            <div className="flex gap-2 items-center">
              <input
                type="text"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Add a note about this trade..."
                className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-blue-500"
                autoFocus
              />
              <button
                onClick={saveNote}
                disabled={saving}
                className="px-2 py-1 text-xs bg-blue-600 rounded text-white hover:bg-blue-500 disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-2 py-1 text-xs bg-gray-700 rounded text-gray-300 hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch { return iso; }
}
