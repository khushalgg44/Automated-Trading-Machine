import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";

interface SessionStatsData {
  session_start: string;
  total_pnl: number;
  todays_trades: number;
  total_signals: number;
  total_rejections: number;
  active_strategy_count: number;
  total_strategy_count: number;
}

export default function SessionStats() {
  const { data } = usePolling<SessionStatsData>("/api/session-stats", 2000);

  if (!data) return null;

  const duration = getSessionDuration(data.session_start);
  const rejectionRate =
    data.total_signals > 0
      ? ((data.total_rejections / (data.total_signals + data.total_rejections)) * 100).toFixed(0)
      : "0";

  return (
    <div className="bg-gray-850 border-b border-gray-700 px-4 py-2">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-x-6 gap-y-1 text-xs font-mono">
        <Stat label="Session" value={duration} />
        <Stat
          label="P&L"
          value={`${data.total_pnl >= 0 ? "+" : ""}${formatCurrency(data.total_pnl)}`}
          color={data.total_pnl >= 0 ? "text-green-400" : "text-red-400"}
        />
        <Stat label="Trades" value={String(data.todays_trades)} />
        <Stat label="Signals" value={String(data.total_signals)} />
        <Stat label="Rejections" value={`${rejectionRate}%`} color={parseInt(rejectionRate) > 20 ? "text-red-400" : "text-gray-300"} />
        <Stat label="Strategies" value={`${data.active_strategy_count}/${data.total_strategy_count}`} />
      </div>
    </div>
  );
}

function Stat({ label, value, color = "text-gray-300" }: { label: string; value: string; color?: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="text-gray-500">{label}:</span>
      <span className={color}>{value}</span>
    </span>
  );
}

function getSessionDuration(startIso: string): string {
  try {
    const start = new Date(startIso);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const hours = Math.floor(diffMs / 3600000);
    const mins = Math.floor((diffMs % 3600000) / 60000);
    return `${String(hours).padStart(2, "0")}h ${String(mins).padStart(2, "0")}m`;
  } catch {
    return "—";
  }
}
