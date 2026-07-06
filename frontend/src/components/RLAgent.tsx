import { useState, useEffect } from "react";
import { usePolling } from "../hooks/usePolling";

interface TrainResult {
  symbol: string;
  timesteps: number;
  total_reward: number;
  trades: number;
  final_return_pct: number;
  actions: { BUY: number; SELL: number; HOLD: number };
  equity_curve: number[];
}

interface RLStatus {
  trained_models: string[];
  deployed: boolean;
  confidence: { symbol?: string; position?: string; entry_price?: number; confidence?: Record<string, number> };
  training_progress: { symbol: string; current_step: number; total_steps: number; percent: number; status: string } | null;
}

export default function RLAgent() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [timesteps, setTimesteps] = useState(20000);
  const [training, setTraining] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [result, setResult] = useState<TrainResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Poll status (includes progress during training)
  const { data: status } = usePolling<RLStatus>("/api/rl/status", training ? 1000 : 5000);

  const handleTrain = async () => {
    setTraining(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/rl/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, timesteps }),
      });
      const data = await res.json();
      if (!res.ok) setError(data.detail || "Training failed");
      else setResult(data);
    } catch (err: any) {
      setError(err.message || "Network error");
    } finally {
      setTraining(false);
    }
  };

  const handleDeploy = async (sym: string) => {
    setDeploying(true);
    try {
      const res = await fetch(`/api/rl/deploy/${sym}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) setError(data.detail);
    } catch { /* silent */ }
    finally { setDeploying(false); }
  };

  const progress = status?.training_progress;
  const isTrainingOnServer = training && progress && (progress.status === "training" || progress.status === "starting");

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          AI Trading Agent (Reinforcement Learning)
        </h2>
        {status?.deployed && (
          <span className="text-xs bg-green-900/40 text-green-400 px-2 py-0.5 rounded border border-green-800">LIVE</span>
        )}
      </div>

      <p className="text-xs text-gray-500 mb-4">
        Train a PPO agent on historical data. The agent learns BUY/SELL/HOLD by maximizing profit through trial and error. Penalized for inactivity.
      </p>

      {/* Training Controls */}
      <div className="flex flex-wrap gap-3 items-end mb-4">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Symbol</label>
          <input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white w-32 focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Training Steps</label>
          <select value={timesteps} onChange={(e) => setTimesteps(Number(e.target.value))}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            <option value={10000}>10K (Fast, ~1 min)</option>
            <option value={20000}>20K (Normal, ~2 min)</option>
            <option value={50000}>50K (Better, ~5 min)</option>
            <option value={100000}>100K (Best, ~10 min)</option>
          </select>
        </div>
        <button onClick={handleTrain} disabled={training}
          className="px-4 py-2 rounded font-bold text-sm bg-purple-600 hover:bg-purple-500 text-white disabled:opacity-50">
          {training ? "🧠 Training..." : "🧠 Train Agent"}
        </button>
      </div>

      {/* Progress Bar */}
      {training && progress && progress.percent < 100 && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Training {progress.symbol}...</span>
            <span>{progress.percent}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-purple-500 rounded-full transition-all duration-500"
              style={{ width: `${progress.percent}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Step {progress.current_step.toLocaleString()} / {progress.total_steps.toLocaleString()}
          </p>
        </div>
      )}

      {error && <p className="text-red-400 text-xs mb-3">{error}</p>}

      {/* Training Result */}
      {result && (
        <div className="bg-gray-700/30 rounded-lg p-4 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs bg-purple-900/40 text-purple-400 px-2 py-0.5 rounded font-bold">Training Complete</span>
            <span className="text-xs text-gray-400">{result.symbol} • {result.timesteps.toLocaleString()} steps</span>
          </div>
          <div className="grid grid-cols-4 gap-3 mb-3">
            <div className="bg-gray-900/50 rounded p-2">
              <p className="text-xs text-gray-500">Return</p>
              <p className={`text-sm font-mono font-bold ${result.final_return_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                {result.final_return_pct >= 0 ? "+" : ""}{result.final_return_pct}%
              </p>
            </div>
            <div className="bg-gray-900/50 rounded p-2">
              <p className="text-xs text-gray-500">Trades</p>
              <p className="text-sm font-mono font-bold text-white">{result.trades}</p>
            </div>
            <div className="bg-gray-900/50 rounded p-2">
              <p className="text-xs text-gray-500">Buy Actions</p>
              <p className="text-sm font-mono font-bold text-green-400">{result.actions.BUY}</p>
            </div>
            <div className="bg-gray-900/50 rounded p-2">
              <p className="text-xs text-gray-500">Sell Actions</p>
              <p className="text-sm font-mono font-bold text-red-400">{result.actions.SELL}</p>
            </div>
          </div>

          {/* Equity curve */}
          {result.equity_curve.length > 1 && (
            <div className="h-16 mb-3">
              <MiniCurve data={result.equity_curve} />
            </div>
          )}

          <button onClick={() => handleDeploy(result.symbol)} disabled={deploying}
            className="px-4 py-2 rounded font-bold text-sm bg-green-600 hover:bg-green-500 text-white disabled:opacity-50">
            {deploying ? "Deploying..." : "🚀 Deploy as Live Strategy"}
          </button>
        </div>
      )}

      {/* Live Confidence Display */}
      {status?.deployed && status.confidence?.confidence && (
        <div className="bg-gray-700/30 rounded-lg p-3 mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400 font-medium">Agent Thinking ({status.confidence.symbol})</span>
            <span className={`text-xs font-bold ${status.confidence.position === "LONG" ? "text-green-400" : "text-gray-400"}`}>
              {status.confidence.position}
            </span>
          </div>
          <div className="flex gap-2">
            <ConfBar label="HOLD" value={status.confidence.confidence.HOLD || 0} color="bg-gray-500" />
            <ConfBar label="BUY" value={status.confidence.confidence.BUY || 0} color="bg-green-500" />
            <ConfBar label="SELL" value={status.confidence.confidence.SELL || 0} color="bg-red-500" />
          </div>
        </div>
      )}

      {/* Trained Models */}
      {status && status.trained_models.length > 0 && (
        <div>
          <h3 className="text-xs text-gray-500 mb-2">Trained Models:</h3>
          <div className="flex gap-2 flex-wrap">
            {status.trained_models.map((sym) => (
              <div key={sym} className="flex items-center gap-1 bg-gray-700/50 rounded px-2 py-1">
                <span className="text-xs text-white font-medium">{sym}</span>
                <button onClick={() => handleDeploy(sym)}
                  className="text-xs text-green-400 hover:text-green-300 ml-1">Deploy</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConfBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex-1">
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-300 font-mono">{value}%</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function MiniCurve({ data }: { data: number[] }) {
  const width = 400;
  const height = 60;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(" ");

  const isProfit = data[data.length - 1] >= data[0];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
      <polyline points={points} fill="none" stroke={isProfit ? "#4ade80" : "#f87171"} strokeWidth="2" />
    </svg>
  );
}
