import { useState } from "react";
import { usePolling } from "../hooks/usePolling";
import { Portfolio } from "../types";
import { formatCurrency } from "../utils";

export default function PortfolioCard() {
  const { data, error, loading } = usePolling<Portfolio>("/api/portfolio", 2000);
  const [resetting, setResetting] = useState(false);

  const handleReset = async () => {
    if (!confirm("Reset portfolio to ₹10,00,000? All trades will be cleared.")) return;
    setResetting(true);
    try {
      await fetch("/api/reset-portfolio", { method: "POST" });
    } catch {
      // silent
    } finally {
      setResetting(false);
    }
  };

  if (loading) return <CardSkeleton />;
  if (error || !data) return <CardError message={error || "No data"} />;

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700 relative">
      <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">
        Portfolio Summary
      </h2>
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Initial Capital" value={formatCurrency(data.initial_capital)} />
        <Stat label="Cash Available" value={formatCurrency(data.capital_available)} />
        <Stat label="Open Positions" value={String(data.positions_count)} />
        <Stat label="Total Trades" value={String(data.total_trades)} />
      </div>
      <button
        onClick={handleReset}
        disabled={resetting}
        className="absolute bottom-4 right-4 text-xs px-2.5 py-1 rounded bg-orange-900/50 text-orange-400 border border-orange-800 hover:bg-orange-900/80 transition-colors disabled:opacity-50"
      >
        {resetting ? "Resetting..." : "Reset"}
      </button>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-lg font-mono font-semibold text-white">{value}</p>
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700 animate-pulse">
      <div className="h-4 bg-gray-700 rounded w-32 mb-4" />
      <div className="grid grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i}>
            <div className="h-3 bg-gray-700 rounded w-20 mb-1" />
            <div className="h-6 bg-gray-700 rounded w-28" />
          </div>
        ))}
      </div>
    </div>
  );
}

function CardError({ message }: { message: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-red-900/50">
      <p className="text-red-400 text-sm">{message}</p>
    </div>
  );
}
