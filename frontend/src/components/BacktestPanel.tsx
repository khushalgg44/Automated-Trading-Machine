import { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface BacktestResult {
  strategy: string;
  symbol: string;
  candles_processed: number;
  final_equity: string;
  total_return_pct: string;
  total_trades: number;
  win_rate: string;
  max_drawdown: string;
  trades: any[];
  equity_curve: { candle: number; date: string; equity: number }[];
  error?: string;
}

interface CompareResponse {
  results: BacktestResult[];
}

const STRATEGY_COLORS: Record<string, string> = {
  ema_cross: "#4ade80",
  rsi_mean_reversion: "#60a5fa",
  bollinger_bands: "#a78bfa",
};

const ALL_STRATEGIES = ["ema_cross", "rsi_mean_reversion", "bollinger_bands"];

export default function BacktestPanel() {
  const [strategy, setStrategy] = useState("ema_cross");
  const [symbol, setSymbol] = useState("RELIANCE");
  const [file, setFile] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [compareResults, setCompareResults] = useState<BacktestResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load available files
  useEffect(() => {
    fetch("/api/backtest/files")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setFiles(data);
          setFile(data[0]);
        }
      })
      .catch(() => {});
  }, []);

  const runBacktest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCompareResults(null);

    try {
      const res = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy, symbol, file }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Backtest failed");
      } else {
        setResult(data);
      }
    } catch (err: any) {
      setError(err.message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  const runCompare = async () => {
    setComparing(true);
    setError(null);
    setResult(null);
    setCompareResults(null);

    try {
      const res = await fetch("/api/backtest/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategies: ALL_STRATEGIES, symbol, file }),
      });

      const data: CompareResponse = await res.json();
      if (!res.ok) {
        setError((data as any).detail || "Compare failed");
      } else {
        setCompareResults(data.results.filter((r) => !r.error));
      }
    } catch (err: any) {
      setError(err.message || "Network error");
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">
        Backtesting
      </h2>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 mb-4 items-end">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Strategy</label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            <option value="ema_cross">EMA Cross</option>
            <option value="rsi_mean_reversion">RSI Mean Reversion</option>
            <option value="bollinger_bands">Bollinger Bands</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Symbol</label>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white w-32 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Data File</label>
          <select
            value={file}
            onChange={(e) => setFile(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            {files.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={runBacktest}
          disabled={loading || comparing}
          className="px-4 py-2 rounded font-bold text-sm bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 disabled:cursor-wait"
        >
          {loading ? <Spinner text="Running..." /> : "Run Backtest"}
        </button>

        <button
          onClick={runCompare}
          disabled={loading || comparing}
          className="px-4 py-2 rounded font-bold text-sm bg-purple-600 hover:bg-purple-500 text-white transition-colors disabled:opacity-50 disabled:cursor-wait"
        >
          {comparing ? <Spinner text="Comparing..." /> : "Compare All"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="text-sm px-3 py-2 rounded bg-red-900/40 text-red-400 border border-red-800 mb-4">
          {error}
        </div>
      )}

      {/* Single backtest result */}
      {result && <SingleResult result={result} />}

      {/* Compare results */}
      {compareResults && compareResults.length > 0 && (
        <CompareResults results={compareResults} />
      )}
    </div>
  );
}

// ─── Single Backtest Result ───────────────────────────────────────────────────

function SingleResult({ result }: { result: BacktestResult }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span
          className="text-xs px-2 py-0.5 rounded font-bold"
          style={{ backgroundColor: `${STRATEGY_COLORS[result.strategy]}20`, color: STRATEGY_COLORS[result.strategy] }}
        >
          {result.strategy}
        </span>
        <span className="text-xs text-gray-400">
          {result.symbol} • {result.candles_processed} candles
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <StatBox label="Final Equity" value={`₹${result.final_equity}`} />
        <StatBox
          label="Return"
          value={`${parseFloat(result.total_return_pct) >= 0 ? "+" : ""}${result.total_return_pct}%`}
          color={parseFloat(result.total_return_pct) >= 0 ? "text-green-400" : "text-red-400"}
        />
        <StatBox label="Trades" value={String(result.total_trades)} />
        <StatBox
          label="Win Rate"
          value={`${result.win_rate}%`}
          color={parseFloat(result.win_rate) >= 50 ? "text-green-400" : "text-red-400"}
        />
        <StatBox label="Max DD" value={`₹${result.max_drawdown}`} color="text-red-400" />
      </div>

      {result.equity_curve.length > 0 && (
        <div style={{ width: "100%", height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={result.equity_curve} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 9 }} axisLine={{ stroke: "#374151" }} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} axisLine={{ stroke: "#374151" }} tickLine={false} domain={["auto", "auto"]} tickFormatter={(v: number) => `₹${(v / 100000).toFixed(1)}L`} width={55} />
              <defs>
                <linearGradient id="singleGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={STRATEGY_COLORS[result.strategy] || "#60a5fa"} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={STRATEGY_COLORS[result.strategy] || "#60a5fa"} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="equity" stroke={STRATEGY_COLORS[result.strategy] || "#60a5fa"} strokeWidth={2} fill="url(#singleGradient)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ─── Compare Results ──────────────────────────────────────────────────────────

function CompareResults({ results }: { results: BacktestResult[] }) {
  // Build merged equity curve data for overlaid chart
  const mergedCurve = buildMergedCurve(results);

  // Find best in each metric column
  const bestReturn = Math.max(...results.map((r) => parseFloat(r.total_return_pct)));
  const bestWinRate = Math.max(...results.map((r) => parseFloat(r.win_rate)));
  const lowestDD = Math.min(...results.map((r) => parseFloat(r.max_drawdown)));
  const bestEquity = Math.max(...results.map((r) => parseFloat(r.final_equity)));

  return (
    <div>
      <h3 className="text-sm font-medium text-gray-400 mb-3">Strategy Comparison</h3>

      {/* Comparison table */}
      <div className="overflow-x-auto mb-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs uppercase border-b border-gray-700">
              <th className="text-left pb-2">Strategy</th>
              <th className="text-right pb-2">Final Equity</th>
              <th className="text-right pb-2">Return %</th>
              <th className="text-right pb-2">Trades</th>
              <th className="text-right pb-2">Win Rate</th>
              <th className="text-right pb-2">Max DD</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => {
              const ret = parseFloat(r.total_return_pct);
              const wr = parseFloat(r.win_rate);
              const dd = parseFloat(r.max_drawdown);
              const eq = parseFloat(r.final_equity);

              return (
                <tr key={r.strategy} className="border-b border-gray-700/50">
                  <td className="py-2">
                    <span className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: STRATEGY_COLORS[r.strategy] }}
                      />
                      <span className="text-white font-medium">{r.strategy}</span>
                    </span>
                  </td>
                  <td className={`py-2 text-right font-mono ${eq === bestEquity ? "text-green-400 font-bold" : "text-white"}`}>
                    ₹{r.final_equity}
                  </td>
                  <td className={`py-2 text-right font-mono ${ret === bestReturn ? "text-green-400 font-bold" : ret >= 0 ? "text-white" : "text-red-400"}`}>
                    {ret >= 0 ? "+" : ""}{r.total_return_pct}%
                  </td>
                  <td className="py-2 text-right font-mono text-white">
                    {r.total_trades}
                  </td>
                  <td className={`py-2 text-right font-mono ${wr === bestWinRate ? "text-green-400 font-bold" : "text-white"}`}>
                    {r.win_rate}%
                  </td>
                  <td className={`py-2 text-right font-mono ${dd === lowestDD ? "text-green-400 font-bold" : "text-red-400"}`}>
                    ₹{r.max_drawdown}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Overlaid equity curves */}
      {mergedCurve.length > 0 && (
        <div style={{ width: "100%", height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mergedCurve} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 9 }} axisLine={{ stroke: "#374151" }} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} axisLine={{ stroke: "#374151" }} tickLine={false} domain={["auto", "auto"]} tickFormatter={(v: number) => `₹${(v / 100000).toFixed(1)}L`} width={55} />
              <Legend
                wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                iconType="circle"
                iconSize={8}
              />
              {results.map((r) => (
                <Line
                  key={r.strategy}
                  type="monotone"
                  dataKey={r.strategy}
                  name={r.strategy}
                  stroke={STRATEGY_COLORS[r.strategy]}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildMergedCurve(results: BacktestResult[]): Record<string, any>[] {
  // Merge equity curves from all strategies into one dataset for overlaid chart
  if (results.length === 0) return [];

  const maxLen = Math.max(...results.map((r) => r.equity_curve.length));
  const merged: Record<string, any>[] = [];

  for (let i = 0; i < maxLen; i++) {
    const point: Record<string, any> = {};
    // Use date from first result that has this index
    for (const r of results) {
      if (r.equity_curve[i]) {
        point.date = r.equity_curve[i].date;
        point[r.strategy] = r.equity_curve[i].equity;
      }
    }
    if (point.date) merged.push(point);
  }

  return merged;
}

function Spinner({ text }: { text: string }) {
  return (
    <span className="flex items-center gap-2">
      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {text}
    </span>
  );
}

function StatBox({ label, value, color = "text-white" }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-gray-900/50 rounded p-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-sm font-mono font-semibold ${color}`}>{value}</p>
    </div>
  );
}
