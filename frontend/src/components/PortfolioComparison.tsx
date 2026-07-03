import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";
import { Trade } from "../types";

interface StrategyStats {
  name: string;
  trades: number;
  totalPnl: number;
  winRate: number;
}

function computeStrategyStats(trades: Trade[], strategy: string, displayName: string): StrategyStats {
  const filtered = trades.filter(
    (t) => t.strategy === strategy && t.direction === "SELL" && t.pnl !== 0
  );
  const wins = filtered.filter((t) => t.pnl > 0).length;
  const totalPnl = filtered.reduce((sum, t) => sum + t.pnl, 0);
  const winRate = filtered.length > 0 ? (wins / filtered.length) * 100 : 0;

  return {
    name: displayName,
    trades: filtered.length,
    totalPnl,
    winRate,
  };
}

export default function PortfolioComparison() {
  const { data: trades } = usePolling<Trade[]>("/api/trades", 5000);

  if (!trades || trades.length === 0) return null;

  const emaStats = computeStrategyStats(trades, "ema_cross", "EMA Cross");
  const rsiStats = computeStrategyStats(trades, "rsi_mean_reversion", "RSI Mean Rev");

  // Only show if there's data for at least one strategy
  if (emaStats.trades === 0 && rsiStats.trades === 0) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
        Strategy Comparison
      </h2>
      <div className="grid grid-cols-2 gap-3">
        <StrategyCard stats={emaStats} />
        <StrategyCard stats={rsiStats} />
      </div>
    </div>
  );
}

function StrategyCard({ stats }: { stats: StrategyStats }) {
  const pnlColor = stats.totalPnl >= 0 ? "text-green-400" : "text-red-400";
  const winColor = stats.winRate >= 50 ? "text-green-400" : stats.winRate > 0 ? "text-yellow-400" : "text-gray-500";

  return (
    <div className="bg-gray-700/50 rounded-lg p-3">
      <p className="text-xs font-medium text-gray-300 mb-2">{stats.name}</p>
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">Trades</span>
          <span className="text-white font-mono">{stats.trades}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">P&L</span>
          <span className={`font-mono ${pnlColor}`}>
            {formatCurrency(stats.totalPnl)}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">Win Rate</span>
          <span className={`font-mono ${winColor}`}>
            {stats.winRate.toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}
