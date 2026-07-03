import { useState, useEffect, useRef } from "react";
import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";

interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  in_progress?: boolean;
}

interface SearchResult {
  symbol: string;
  name: string;
  token: string;
}

// Persist symbol across tab switches
let _persistedSymbol = "RELIANCE";
let _persistedPeriod = "live";

export default function HistoricalChart() {
  const [symbol, setSymbol] = useState(_persistedSymbol);
  const [period, setPeriod] = useState(_persistedPeriod);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearch, setShowSearch] = useState(false);
  const [showEMA, setShowEMA] = useState(false);
  const [showBB, setShowBB] = useState(false);
  const [hoveredCandle, setHoveredCandle] = useState<Candle | null>(null);

  // Live candle polling (only when period is "live")
  const { data: liveCandles } = usePolling<Candle[]>(
    period === "live" ? `/api/candles/${symbol}?timeframe=1m` : "",
    period === "live" ? 2000 : 999999
  );

  // Use live candles when in live mode
  useEffect(() => {
    if (period === "live" && liveCandles) {
      setCandles(liveCandles);
    }
  }, [liveCandles, period]);

  // Persist symbol
  useEffect(() => { _persistedSymbol = symbol; }, [symbol]);
  useEffect(() => { _persistedPeriod = period; }, [period]);

  const fetchHistorical = (sym: string, days: number) => {
    const toDate = new Date().toISOString().split("T")[0];
    const fromDate = new Date(Date.now() - days * 86400000).toISOString().split("T")[0];
    let interval = "day";
    if (days <= 1) interval = "minute";
    else if (days <= 5) interval = "5minute";
    else if (days <= 30) interval = "15minute";
    else if (days <= 60) interval = "60minute";

    setLoading(true);
    setError(null);
    fetch(`/api/historical/${sym}?from_date=${fromDate}&to_date=${toDate}&interval=${interval}`)
      .then(r => r.json())
      .then(data => {
        if (data.detail) setError(data.detail);
        else setCandles(data.candles || []);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  const handlePeriod = (p: string, days: number) => {
    setPeriod(p);
    if (p === "live") return; // will use polling
    fetchHistorical(symbol, days);
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
    if (period !== "live") {
      const days = periodToDays(period);
      if (days) fetchHistorical(sym, days);
    }
  };

  const displayCandles = candles;
  const lastCandle = displayCandles[displayCandles.length - 1];
  const sessionHigh = displayCandles.length > 0 ? Math.max(...displayCandles.map(c => c.high)) : 0;
  const sessionLow = displayCandles.length > 0 ? Math.min(...displayCandles.map(c => c.low)) : 0;

  // Indicators (computed client-side)
  const emaFast = showEMA ? computeEMA(displayCandles.map(c => c.close), 9) : [];
  const emaSlow = showEMA ? computeEMA(displayCandles.map(c => c.close), 21) : [];
  const { upper: bbUpper, middle: bbMiddle, lower: bbLower } = showBB
    ? computeBB(displayCandles.map(c => c.close), 20, 2) : { upper: [], middle: [], lower: [] };

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      {/* Header row */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          {/* Symbol search */}
          <div className="relative">
            <input
              value={showSearch ? searchQuery : symbol}
              onFocus={() => setShowSearch(true)}
              onBlur={() => setTimeout(() => setShowSearch(false), 200)}
              onChange={(e) => { setShowSearch(true); searchSymbol(e.target.value); }}
              className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-white w-32 focus:outline-none focus:border-blue-500 font-bold"
            />
            {showSearch && searchResults.length > 0 && (
              <div className="absolute z-50 top-full mt-1 w-64 bg-gray-900 border border-gray-700 rounded shadow-xl max-h-48 overflow-y-auto">
                {searchResults.map((r) => (
                  <button key={r.symbol} onMouseDown={() => selectSymbol(r.symbol)}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-700 text-gray-300">
                    <span className="font-bold text-white">{r.symbol}</span>
                    <span className="text-gray-500 ml-2">{r.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {lastCandle && (
            <span className={`font-mono text-lg font-bold ${lastCandle.close >= lastCandle.open ? "text-green-400" : "text-red-400"}`}>
              {formatCurrency(lastCandle.close)}
            </span>
          )}
          {displayCandles.length > 0 && (
            <div className="flex gap-3 text-xs text-gray-400 font-mono hidden sm:flex">
              <span>H: <span className="text-green-400">{formatCurrency(sessionHigh)}</span></span>
              <span>L: <span className="text-red-400">{formatCurrency(sessionLow)}</span></span>
              <span className="text-gray-600">{displayCandles.length} candles</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button onClick={() => setShowEMA(!showEMA)}
            className={`text-xs px-2 py-1 rounded border ${showEMA ? "bg-blue-900/40 text-blue-400 border-blue-700" : "text-gray-500 border-gray-700"}`}>EMA</button>
          <button onClick={() => setShowBB(!showBB)}
            className={`text-xs px-2 py-1 rounded border ${showBB ? "bg-purple-900/40 text-purple-400 border-purple-700" : "text-gray-500 border-gray-700"}`}>BB</button>
        </div>
      </div>

      {/* Period buttons */}
      <div className="flex gap-1 mb-3">
        {[
          { label: "Live", id: "live", days: 0 },
          { label: "1d", id: "1d", days: 1 },
          { label: "5d", id: "5d", days: 5 },
          { label: "1m", id: "1m", days: 30 },
          { label: "3m", id: "3m", days: 90 },
          { label: "6m", id: "6m", days: 180 },
          { label: "1y", id: "1y", days: 365 },
          { label: "5y", id: "5y", days: 1800 },
        ].map(({ label, id, days }) => (
          <button key={id}
            onClick={() => handlePeriod(id, days)}
            className={`px-2.5 py-1 text-xs rounded transition-colors ${
              period === id ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-400 hover:text-white"
            }`}>
            {label}
          </button>
        ))}
      </div>

      {/* Hover tooltip */}
      {hoveredCandle && (
        <div className="text-xs font-mono text-gray-300 mb-1 flex gap-4">
          <span>{formatFullDate(hoveredCandle.timestamp)}</span>
          <span>O: {formatCurrency(hoveredCandle.open)}</span>
          <span>H: <span className="text-green-400">{formatCurrency(hoveredCandle.high)}</span></span>
          <span>L: <span className="text-red-400">{formatCurrency(hoveredCandle.low)}</span></span>
          <span>C: {formatCurrency(hoveredCandle.close)}</span>
          <span>Vol: {hoveredCandle.volume.toLocaleString()}</span>
        </div>
      )}

      {error && <p className="text-red-400 text-xs mb-2">{error}</p>}
      {loading && <p className="text-gray-500 text-xs mb-2">Loading...</p>}

      {/* Chart */}
      {displayCandles.length > 1 ? (
        <>
          <ChartSVG candles={displayCandles} emaFast={emaFast} emaSlow={emaSlow}
            bbUpper={bbUpper} bbMiddle={bbMiddle} bbLower={bbLower}
            showEMA={showEMA} showBB={showBB} period={period}
            onHover={setHoveredCandle} />
          <VolumeBars candles={displayCandles} />
        </>
      ) : !loading && (
        <div className="h-[300px] flex items-center justify-center text-gray-500 text-sm">
          {period === "live" ? "Waiting for candle data..." : "Select a period to load data"}
        </div>
      )}
    </div>
  );
}

// ─── Chart SVG ────────────────────────────────────────────────────────────────

function ChartSVG({ candles, emaFast, emaSlow, bbUpper, bbMiddle, bbLower, showEMA, showBB, period, onHover }: {
  candles: Candle[]; emaFast: (number|null)[]; emaSlow: (number|null)[];
  bbUpper: (number|null)[]; bbMiddle: (number|null)[]; bbLower: (number|null)[];
  showEMA: boolean; showBB: boolean; period: string;
  onHover: (c: Candle | null) => void;
}) {
  const width = 960;
  const height = 320;
  const pad = { top: 10, bottom: 25, left: 55, right: 10 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;

  const allHigh = Math.max(...candles.map(c => c.high));
  const allLow = Math.min(...candles.map(c => c.low));
  const range = allHigh - allLow || 1;

  const candleW = Math.max(1, (chartW / candles.length) * 0.7);
  const yScale = (p: number) => pad.top + chartH - ((p - allLow) / range) * chartH;
  const xCenter = (i: number) => pad.left + ((i + 0.5) / candles.length) * chartW;

  const buildLine = (vals: (number|null)[]): string =>
    vals.map((v, i) => v !== null ? `${xCenter(i)},${yScale(v)}` : "").filter(Boolean).join(" ");

  const yLabels = 6;
  const yStep = range / yLabels;

  // X-axis label interval
  const labelInterval = Math.max(1, Math.floor(candles.length / 8));

  return (
    <div style={{ width: "100%", height: 320, overflow: "hidden" }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full"
        onMouseLeave={() => onHover(null)}>
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
          const pts: string[] = []; const ptsR: string[] = [];
          for (let i = 0; i < candles.length; i++) {
            if (bbUpper[i] !== null && bbLower[i] !== null) {
              pts.push(`${xCenter(i)},${yScale(bbUpper[i]!)}`);
              ptsR.push(`${xCenter(i)},${yScale(bbLower[i]!)}`);
            }
          }
          if (pts.length < 2) return null;
          return <polygon points={[...pts, ...ptsR.reverse()].join(" ")} fill="#a78bfa" opacity={0.05} />;
        })()}

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
            <g key={i} onMouseEnter={() => onHover(c)}>
              <line x1={xCenter(i)} x2={xCenter(i)} y1={yScale(c.high)} y2={yScale(c.low)} stroke={isGreen ? "#4ade80" : "#f87171"} strokeWidth={0.8} />
              <rect x={x} y={bodyTop} width={candleW} height={bodyH} fill={isGreen ? "#4ade80" : "#f87171"} opacity={c.in_progress ? 0.5 : 1} />
              {/* Invisible hover area */}
              <rect x={x - 2} y={pad.top} width={candleW + 4} height={chartH} fill="transparent" />
            </g>
          );
        })}

        {/* EMA */}
        {showEMA && (
          <>
            <polyline points={buildLine(emaFast)} fill="none" stroke="#60a5fa" strokeWidth="1.5" />
            <polyline points={buildLine(emaSlow)} fill="none" stroke="#fb923c" strokeWidth="1.5" />
          </>
        )}

        {/* X-axis */}
        {candles.filter((_, i) => i % labelInterval === 0).map((c, idx) => {
          const i = idx * labelInterval;
          return (
            <text key={i} x={xCenter(i)} y={height - 5} textAnchor="middle" fill="#9ca3af" fontSize="8" fontFamily="monospace">
              {formatXLabel(c.timestamp, period)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

function VolumeBars({ candles }: { candles: Candle[] }) {
  const maxVol = Math.max(...candles.map(c => c.volume));
  if (maxVol === 0) return null;
  return (
    <div className="flex items-end gap-px h-10 mt-1 px-14">
      {candles.map((c, i) => {
        const h = (c.volume / maxVol) * 100;
        return <div key={i} className="flex-1 min-w-0" style={{ height: `${h}%`, backgroundColor: c.close >= c.open ? "#4ade8044" : "#f8717144" }} />;
      })}
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatXLabel(ts: string, period: string): string {
  try {
    const d = new Date(ts);
    if (period === "live" || period === "1d") return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    if (period === "5d") return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" }) + " " + d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    if (period === "1m" || period === "3m") return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
    // 6m, 1y, 5y — show month + year
    return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
  } catch { return ts; }
}

function formatFullDate(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return ts; }
}

function periodToDays(period: string): number | null {
  const map: Record<string, number> = { "1d": 1, "5d": 5, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "5y": 1800 };
  return map[period] || null;
}

function computeEMA(prices: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  if (prices.length < period) return prices.map(() => null);
  const k = 2 / (period + 1);
  let ema = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) result.push(null);
    else if (i === period - 1) result.push(Math.round(ema * 100) / 100);
    else { ema = prices[i] * k + ema * (1 - k); result.push(Math.round(ema * 100) / 100); }
  }
  return result;
}

function computeBB(prices: number[], period: number, mult: number) {
  const upper: (number | null)[] = []; const middle: (number | null)[] = []; const lower: (number | null)[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) { upper.push(null); middle.push(null); lower.push(null); }
    else {
      const w = prices.slice(i - period + 1, i + 1);
      const sma = w.reduce((a, b) => a + b, 0) / period;
      const std = Math.sqrt(w.reduce((a, b) => a + (b - sma) ** 2, 0) / period);
      middle.push(Math.round(sma * 100) / 100);
      upper.push(Math.round((sma + mult * std) * 100) / 100);
      lower.push(Math.round((sma - mult * std) * 100) / 100);
    }
  }
  return { upper, middle, lower };
}
