import { useState } from "react";
import { formatCurrency } from "../utils";

interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface SearchResult {
  symbol: string;
  name: string;
  token: string;
}

export default function HistoricalChart() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [fromDate, setFromDate] = useState(getDefaultFrom());
  const [toDate, setToDate] = useState(getToday());
  const [interval, setInterval] = useState("day");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearch, setShowSearch] = useState(false);
  const [showEMA, setShowEMA] = useState(false);
  const [showBB, setShowBB] = useState(false);

  const fetchData = async () => {
    fetchWithParams(symbol, fromDate, toDate, interval);
  };

  const fetchWithParams = async (sym: string, f: string, t: string, intv: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/historical/${sym}?from_date=${f}&to_date=${t}&interval=${intv}`);
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Failed to fetch");
      } else {
        setCandles(data.candles);
      }
    } catch (err: any) {
      setError(err.message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  const searchSymbol = async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) { setSearchResults([]); return; }
    try {
      const res = await fetch(`/api/historical/search/${query}`);
      const data = await res.json();
      if (Array.isArray(data)) setSearchResults(data);
    } catch { /* silent */ }
  };

  const selectSymbol = (sym: string) => {
    setSymbol(sym);
    setShowSearch(false);
    setSearchQuery("");
    setSearchResults([]);
    fetchWithParams(sym, fromDate, toDate, interval);
  };

  // Compute indicators client-side for the loaded data
  const emaFast = showEMA ? computeEMA(candles.map(c => c.close), 9) : [];
  const emaSlow = showEMA ? computeEMA(candles.map(c => c.close), 21) : [];
  const { upper: bbUpper, middle: bbMiddle, lower: bbLower } = showBB
    ? computeBB(candles.map(c => c.close), 20, 2)
    : { upper: [], middle: [], lower: [] };

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">
        Historical Data Explorer
      </h2>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 mb-4 items-end">
        {/* Symbol with search */}
        <div className="relative">
          <label className="text-xs text-gray-500 block mb-1">Symbol</label>
          <input
            value={showSearch ? searchQuery : symbol}
            onFocus={() => setShowSearch(true)}
            onChange={(e) => { setShowSearch(true); searchSymbol(e.target.value); }}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white w-36 focus:outline-none focus:border-blue-500"
            placeholder="Search..."
          />
          {showSearch && searchResults.length > 0 && (
            <div className="absolute z-20 top-full mt-1 w-64 bg-gray-900 border border-gray-700 rounded shadow-xl max-h-48 overflow-y-auto">
              {searchResults.map((r) => (
                <button
                  key={r.symbol}
                  onClick={() => selectSymbol(r.symbol)}
                  className="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-700 text-gray-300"
                >
                  <span className="font-bold text-white">{r.symbol}</span>
                  <span className="text-gray-500 ml-2">{r.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Period</label>
          <div className="flex gap-1">
            {[
              { label: "1d", days: 1 },
              { label: "5d", days: 5 },
              { label: "1m", days: 30 },
              { label: "3m", days: 90 },
              { label: "6m", days: 180 },
              { label: "1y", days: 365 },
              { label: "5y", days: 1800 },
            ].map(({ label, days }) => (
              <button key={label} onClick={() => {
                const newFrom = daysAgo(days);
                const newTo = getToday();
                let newInterval = "day";
                if (days <= 1) newInterval = "minute";
                else if (days <= 5) newInterval = "5minute";
                else if (days <= 30) newInterval = "15minute";
                else if (days <= 60) newInterval = "60minute";
                setFromDate(newFrom);
                setToDate(newTo);
                setInterval(newInterval);
                // Fetch immediately
                fetchWithParams(symbol, newFrom, newTo, newInterval);
              }}
                className="px-2 py-1.5 text-xs bg-gray-900 border border-gray-700 rounded text-gray-400 hover:text-white hover:border-gray-500">
                {label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">From</label>
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">To</label>
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Interval</label>
          <select value={interval} onChange={(e) => setInterval(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            <option value="minute">1 Min</option>
            <option value="5minute">5 Min</option>
            <option value="15minute">15 Min</option>
            <option value="30minute">30 Min</option>
            <option value="60minute">1 Hour</option>
            <option value="day">Daily</option>
          </select>
        </div>

        {candles.length > 0 && (
          <>
            <button onClick={() => setShowEMA(!showEMA)}
              className={`text-xs px-2 py-1 rounded border ${showEMA ? "bg-blue-900/40 text-blue-400 border-blue-700" : "text-gray-500 border-gray-700"}`}>
              EMA
            </button>
            <button onClick={() => setShowBB(!showBB)}
              className={`text-xs px-2 py-1 rounded border ${showBB ? "bg-purple-900/40 text-purple-400 border-purple-700" : "text-gray-500 border-gray-700"}`}>
              BB
            </button>
          </>
        )}
      </div>

      {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

      {/* Info bar */}
      {candles.length > 0 && (
        <div className="flex items-center gap-4 text-xs text-gray-400 mb-3">
          <span className="font-bold text-white text-sm">{symbol}</span>
          <span>{candles.length} candles</span>
          <span>H: <span className="text-green-400">{formatCurrency(Math.max(...candles.map(c => c.high)))}</span></span>
          <span>L: <span className="text-red-400">{formatCurrency(Math.min(...candles.map(c => c.low)))}</span></span>
          <span>Last: <span className="text-white">{formatCurrency(candles[candles.length - 1].close)}</span></span>
        </div>
      )}

      {/* Chart */}
      {candles.length > 0 ? (
        <HistCandleSVG candles={candles} emaFast={emaFast} emaSlow={emaSlow} bbUpper={bbUpper} bbMiddle={bbMiddle} bbLower={bbLower} showEMA={showEMA} showBB={showBB} />
      ) : !loading && (
        <div className="h-[350px] flex items-center justify-center text-gray-500 text-sm">
          Select a stock and date range, then click "Fetch Data"
        </div>
      )}

      {/* Volume bars */}
      {candles.length > 0 && <VolumeBars candles={candles} />}
    </div>
  );
}

// ─── Chart Components ─────────────────────────────────────────────────────────

function HistCandleSVG({ candles, emaFast, emaSlow, bbUpper, bbMiddle, bbLower, showEMA, showBB }: {
  candles: Candle[]; emaFast: (number|null)[]; emaSlow: (number|null)[];
  bbUpper: (number|null)[]; bbMiddle: (number|null)[]; bbLower: (number|null)[];
  showEMA: boolean; showBB: boolean;
}) {
  const width = 960;
  const height = 320;
  const pad = { top: 10, bottom: 20, left: 55, right: 10 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;

  const allHigh = Math.max(...candles.map(c => c.high));
  const allLow = Math.min(...candles.map(c => c.low));
  const range = allHigh - allLow || 1;

  const candleW = Math.max(1.5, (chartW / candles.length) * 0.7);
  const yScale = (p: number) => pad.top + chartH - ((p - allLow) / range) * chartH;
  const xCenter = (i: number) => pad.left + ((i + 0.5) / candles.length) * chartW;

  const buildLine = (vals: (number|null)[]): string =>
    vals.map((v, i) => v !== null ? `${xCenter(i)},${yScale(v)}` : "").filter(Boolean).join(" ");

  const yLabels = 6;
  const yStep = range / yLabels;

  return (
    <div style={{ width: "100%", height: 350, overflow: "hidden" }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
        {/* Grid */}
        {Array.from({ length: yLabels + 1 }).map((_, i) => {
          const p = allLow + yStep * i;
          const y = yScale(p);
          return (
            <g key={i}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="#374151" strokeDasharray="2,4" />
              <text x={pad.left - 5} y={y + 3} textAnchor="end" fill="#9ca3af" fontSize="9" fontFamily="monospace">₹{p.toFixed(0)}</text>
            </g>
          );
        })}

        {/* BB fill */}
        {showBB && (() => {
          const pts: string[] = [];
          const ptsR: string[] = [];
          for (let i = 0; i < candles.length; i++) {
            if (bbUpper[i] !== null && bbLower[i] !== null) {
              pts.push(`${xCenter(i)},${yScale(bbUpper[i]!)}`);
              ptsR.push(`${xCenter(i)},${yScale(bbLower[i]!)}`);
            }
          }
          if (pts.length < 2) return null;
          return <polygon points={[...pts, ...ptsR.reverse()].join(" ")} fill="#a78bfa" opacity={0.05} />;
        })()}

        {/* BB lines */}
        {showBB && (
          <>
            <polyline points={buildLine(bbUpper)} fill="none" stroke="#f87171" strokeWidth="1" strokeDasharray="3,3" opacity={0.7} />
            <polyline points={buildLine(bbMiddle)} fill="none" stroke="#9ca3af" strokeWidth="1" strokeDasharray="4,4" opacity={0.5} />
            <polyline points={buildLine(bbLower)} fill="none" stroke="#4ade80" strokeWidth="1" strokeDasharray="3,3" opacity={0.7} />
          </>
        )}

        {/* Candles */}
        {candles.map((c, i) => {
          const x = xCenter(i) - candleW / 2;
          const isGreen = c.close >= c.open;
          const bodyTop = yScale(Math.max(c.open, c.close));
          const bodyBot = yScale(Math.min(c.open, c.close));
          const bodyH = Math.max(1, bodyBot - bodyTop);
          return (
            <g key={i}>
              <line x1={xCenter(i)} x2={xCenter(i)} y1={yScale(c.high)} y2={yScale(c.low)} stroke={isGreen ? "#4ade80" : "#f87171"} strokeWidth={0.8} />
              <rect x={x} y={bodyTop} width={candleW} height={bodyH} fill={isGreen ? "#4ade80" : "#f87171"} />
            </g>
          );
        })}

        {/* EMA lines */}
        {showEMA && (
          <>
            <polyline points={buildLine(emaFast)} fill="none" stroke="#60a5fa" strokeWidth="1.5" />
            <polyline points={buildLine(emaSlow)} fill="none" stroke="#fb923c" strokeWidth="1.5" />
          </>
        )}

        {/* X-axis labels */}
        {candles.filter((_, i) => i % Math.max(1, Math.floor(candles.length / 8)) === 0).map((c, idx) => {
          const i = idx * Math.max(1, Math.floor(candles.length / 8));
          return (
            <text key={i} x={xCenter(i)} y={height - 4} textAnchor="middle" fill="#9ca3af" fontSize="8" fontFamily="monospace">
              {formatDate(c.timestamp)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

function VolumeBars({ candles }: { candles: Candle[] }) {
  const maxVol = Math.max(...candles.map(c => c.volume));
  return (
    <div className="flex items-end gap-px h-12 mt-1 px-14">
      {candles.map((c, i) => {
        const h = maxVol > 0 ? (c.volume / maxVol) * 100 : 0;
        const isGreen = c.close >= c.open;
        return (
          <div key={i} className="flex-1 min-w-0"
            style={{ height: `${h}%`, backgroundColor: isGreen ? "#4ade8066" : "#f8717166" }} />
        );
      })}
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function computeEMA(prices: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  if (prices.length < period) return prices.map(() => null);
  const k = 2 / (period + 1);
  let ema = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) { result.push(null); }
    else if (i === period - 1) { result.push(Math.round(ema * 100) / 100); }
    else { ema = prices[i] * k + ema * (1 - k); result.push(Math.round(ema * 100) / 100); }
  }
  return result;
}

function computeBB(prices: number[], period: number, mult: number) {
  const upper: (number | null)[] = [];
  const middle: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) { upper.push(null); middle.push(null); lower.push(null); }
    else {
      const window = prices.slice(i - period + 1, i + 1);
      const sma = window.reduce((a, b) => a + b, 0) / period;
      const std = Math.sqrt(window.reduce((a, b) => a + (b - sma) ** 2, 0) / period);
      middle.push(Math.round(sma * 100) / 100);
      upper.push(Math.round((sma + mult * std) * 100) / 100);
      lower.push(Math.round((sma - mult * std) * 100) / 100);
    }
  }
  return { upper, middle, lower };
}

function formatDate(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
  } catch { return ts; }
}

function getToday(): string {
  return new Date().toISOString().split("T")[0];
}

function getDefaultFrom(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 3);
  return d.toISOString().split("T")[0];
}

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().split("T")[0];
}
