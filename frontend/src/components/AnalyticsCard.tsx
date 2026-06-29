import { usePolling } from "../hooks/usePolling";

interface Analytics {
  total_trades: string;
  win_rate: string;
  avg_profit: string;
  avg_loss: string;
  profit_factor: string;
  max_drawdown: string;
  best_trade: string;
  best_trade_pct: string;
  worst_trade: string;
  worst_trade_pct: string;
}

export default function AnalyticsCard() {
  const { data, error, loading } = usePolling<Analytics>("/api/analytics", 5000);

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-5 border border-gray-700 animate-pulse">
        <div className="h-4 bg-gray-700 rounded w-40 mb-4" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i}>
              <div className="h-3 bg-gray-700 rounded w-20 mb-1" />
              <div className="h-6 bg-gray-700 rounded w-24" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-gray-800 rounded-lg p-5 border border-red-900/50">
        <p className="text-red-400 text-sm">{error || "No data"}</p>
      </div>
    );
  }

  const winRate = parseFloat(data.win_rate);
  const profitFactor = data.profit_factor === "∞" ? 999 : parseFloat(data.profit_factor);

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          Performance Analytics
        </h2>
        <a
          href="/api/export/analytics"
          target="_blank"
          className="text-xs text-gray-500 hover:text-white transition-colors"
          title="Export analytics JSON"
        >
          📥 Export
        </a>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Metric label="Total Trades" value={data.total_trades} />
        <Metric
          label="Win Rate"
          value={`${data.win_rate}%`}
          color={winRate >= 50 ? "text-green-400" : "text-red-400"}
        />
        <Metric label="Avg Profit" value={`₹${data.avg_profit}`} color="text-green-400" />
        <Metric label="Avg Loss" value={`₹${data.avg_loss}`} color="text-red-400" />
        <Metric
          label="Profit Factor"
          value={data.profit_factor}
          color={profitFactor >= 1 ? "text-green-400" : "text-red-400"}
        />
        <Metric label="Max Drawdown" value={`₹${data.max_drawdown}`} color="text-red-400" />
        <Metric
          label="Best Trade"
          value={`₹${data.best_trade} (${data.best_trade_pct}%)`}
          color="text-green-400"
        />
        <Metric
          label="Worst Trade"
          value={`₹${data.worst_trade} (${data.worst_trade_pct}%)`}
          color="text-red-400"
        />
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  color = "text-white",
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-mono font-semibold ${color}`}>{value}</p>
    </div>
  );
}
