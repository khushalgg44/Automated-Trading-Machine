import { useState } from "react";
import { usePolling } from "../hooks/usePolling";
import { Strategy } from "../types";
import StrategyConfig from "./StrategyConfig";

export default function StrategyStatus() {
  const { data, error, loading } = usePolling<Strategy[]>(
    "/api/strategies",
    2000
  );

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">
        Strategies
      </h2>
      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : !data || data.length === 0 ? (
        <p className="text-gray-500 text-sm">No strategies registered</p>
      ) : (
        <div className="space-y-3">
          {data.map((s) => (
            <StrategyRow key={s.name} strategy={s} />
          ))}
        </div>
      )}
    </div>
  );
}

function StrategyRow({ strategy }: { strategy: Strategy }) {
  const [loading, setLoading] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);

  const toggle = async () => {
    setLoading(true);
    const action = strategy.active ? "stop" : "start";
    try {
      await fetch(`/api/strategy/${strategy.name}/${action}`, { method: "POST" });
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-2 px-3 bg-gray-900/50 rounded">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              strategy.active ? "bg-green-400" : "bg-gray-600"
            }`}
          />
          <span className="text-white font-medium text-sm">{strategy.name}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setConfigOpen(!configOpen)}
            className="text-xs px-1.5 py-0.5 rounded text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
            title="Configure"
          >
            ⚙️
          </button>
          <span
            className={`text-xs font-bold px-2 py-0.5 rounded ${
              strategy.active
                ? "bg-green-900/40 text-green-400"
                : "bg-gray-700 text-gray-400"
            }`}
          >
            {strategy.active ? "RUNNING" : "STOPPED"}
          </span>
          <button
            onClick={toggle}
            disabled={loading}
            className={`text-xs px-2 py-0.5 rounded font-bold transition-colors disabled:opacity-50 ${
              strategy.active
                ? "bg-red-900/40 text-red-400 hover:bg-red-900/60 border border-red-800"
                : "bg-green-900/40 text-green-400 hover:bg-green-900/60 border border-green-800"
            }`}
          >
            {strategy.active ? "Stop" : "Start"}
          </button>
        </div>
      </div>
      {/* Config parameters */}
      {strategy.config && Object.keys(strategy.config).length > 0 && !configOpen && (
        <p className="text-xs text-gray-500 mt-1 ml-4">
          {formatConfig(strategy.name, strategy.config)}
        </p>
      )}
      {/* Config editor */}
      {configOpen && (
        <StrategyConfig
          strategyName={strategy.name}
          currentConfig={strategy.config}
          onClose={() => setConfigOpen(false)}
          onSuccess={() => {}}
        />
      )}
    </div>
  );
}

function formatConfig(name: string, config: Record<string, number>): string {
  if (name === "ema_cross") {
    return `Fast: ${config.fast_period}, Slow: ${config.slow_period}`;
  }
  if (name === "rsi_mean_reversion") {
    return `Period: ${config.period}, Oversold: ${config.oversold}, Overbought: ${config.overbought}`;
  }
  if (name === "bollinger_bands") {
    return `Period: ${config.period}, StdDev: ${config.std_dev}`;
  }
  return Object.entries(config)
    .map(([k, v]) => `${k}: ${v}`)
    .join(", ");
}
