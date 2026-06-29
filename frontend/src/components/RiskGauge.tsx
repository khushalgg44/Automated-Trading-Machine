import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";

interface RiskStatus {
  positions_used: number;
  positions_max: number;
  daily_loss_current: number;
  daily_loss_max: number;
  capital_deployed_percent: number;
  capital_available: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "MAXED";
}

export default function RiskGauge() {
  const { data } = usePolling<RiskStatus>("/api/risk-status", 2000);

  if (!data) return null;

  const positionPct = (data.positions_used / data.positions_max) * 100;
  const lossPct = data.daily_loss_max > 0 ? (data.daily_loss_current / data.daily_loss_max) * 100 : 0;

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">Risk</h2>
        <RiskBadge level={data.risk_level} />
      </div>

      <div className="space-y-3">
        {/* Positions bar */}
        <ProgressRow
          label={`Positions: ${data.positions_used}/${data.positions_max}`}
          percent={positionPct}
          color={positionPct >= 80 ? "bg-red-400" : positionPct >= 50 ? "bg-yellow-400" : "bg-green-400"}
        />

        {/* Daily loss bar */}
        <ProgressRow
          label={`Daily Loss: ${formatCurrency(data.daily_loss_current)} / ${formatCurrency(data.daily_loss_max)}`}
          percent={lossPct}
          color={lossPct >= 80 ? "bg-red-400" : lossPct >= 50 ? "bg-yellow-400" : "bg-green-400"}
        />

        {/* Capital deployed */}
        <ProgressRow
          label={`Capital Deployed: ${data.capital_deployed_percent.toFixed(0)}%`}
          percent={data.capital_deployed_percent}
          color={data.capital_deployed_percent >= 80 ? "bg-orange-400" : "bg-blue-400"}
        />
      </div>
    </div>
  );
}

function ProgressRow({ label, percent, color }: { label: string; percent: number; color: string }) {
  const clamped = Math.min(100, Math.max(0, percent));
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{label}</span>
        <span className="font-mono">{clamped.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    LOW: "bg-green-900/40 text-green-400 border-green-800",
    MEDIUM: "bg-yellow-900/40 text-yellow-400 border-yellow-800",
    HIGH: "bg-orange-900/40 text-orange-400 border-orange-800",
    MAXED: "bg-red-900/40 text-red-400 border-red-800",
  };
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded border ${colors[level] || colors.LOW}`}>
      {level}
    </span>
  );
}
