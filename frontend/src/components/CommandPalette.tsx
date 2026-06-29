import { useState, useEffect, useRef } from "react";

interface Command {
  id: string;
  label: string;
  action: () => void;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  watchlist: string[];
  strategies: string[];
  onOpenReport?: () => void;
  onOpenArchDocs?: () => void;
}

export default function CommandPalette({ isOpen, onClose, watchlist, strategies, onOpenReport, onOpenArchDocs }: Props) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: Command[] = [
    ...watchlist.map((s) => ({
      id: `buy-${s}`, label: `Buy ${s}`,
      action: () => { triggerTrade(s, "BUY"); onClose(); },
    })),
    ...watchlist.map((s) => ({
      id: `sell-${s}`, label: `Sell ${s}`,
      action: () => { triggerTrade(s, "SELL"); onClose(); },
    })),
    ...strategies.map((s) => ({
      id: `start-${s}`, label: `Start ${s}`,
      action: () => { fetch(`/api/strategy/${s}/start`, { method: "POST" }); onClose(); },
    })),
    ...strategies.map((s) => ({
      id: `stop-${s}`, label: `Stop ${s}`,
      action: () => { fetch(`/api/strategy/${s}/stop`, { method: "POST" }); onClose(); },
    })),
    { id: "reset", label: "Reset Portfolio", action: () => { if (confirm("Reset portfolio?")) fetch("/api/reset-portfolio", { method: "POST" }); onClose(); } },
    { id: "export", label: "Export Trades", action: () => { window.open("/api/export/trades", "_blank"); onClose(); } },
    { id: "report", label: "Generate Report", action: () => { if (onOpenReport) onOpenReport(); else onClose(); } },
    { id: "architecture", label: "Architecture Docs", action: () => { if (onOpenArchDocs) onOpenArchDocs(); else onClose(); } },
    { id: "backtest", label: "Run Backtest", action: () => { document.querySelector('[data-section="backtest"]')?.scrollIntoView({ behavior: "smooth" }); onClose(); } },
  ];

  const filtered = query
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    if (e.key === "Enter" && filtered.length > 0) {
      filtered[0].action();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative bg-gray-800 border border-gray-600 rounded-xl shadow-2xl w-full max-w-md overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a command..."
          className="w-full bg-transparent px-4 py-3 text-white text-sm border-b border-gray-700 focus:outline-none placeholder-gray-500"
        />
        <div className="max-h-64 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <p className="px-4 py-3 text-gray-500 text-sm">No matching commands</p>
          ) : (
            filtered.slice(0, 10).map((cmd) => (
              <button
                key={cmd.id}
                onClick={cmd.action}
                className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
              >
                {cmd.label}
              </button>
            ))
          )}
        </div>
        <div className="px-4 py-2 border-t border-gray-700 text-xs text-gray-500">
          ↵ Execute • Esc Close
        </div>
      </div>
    </div>
  );
}

async function triggerTrade(symbol: string, side: string) {
  await fetch("/api/manual-trade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, side, quantity: 10 }),
  });
}
