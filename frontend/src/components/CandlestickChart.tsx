import { useState, useEffect } from "react";
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

interface Indicators {
  ema_fast: (number | null)[];
  ema_slow: (number | null)[];
  bb_upper: (number | null)[];
  bb_middle: (number | null)[];
  bb_lower: (number | null)[];
}

interface Props {
  watchlist: string[];
  chartSymbolIndex?: number;
}

export default function CandlestickChart({ watchlist, chartSymbolIndex }: Props) {
  const [symbol, setSymbol] = useState(watchlist[0] || "RELIANCE");
  const [timeframe, setTimeframe] = useState<"1m" | "5m">("1m");
  const [showEMA, setShowEMA] = useState(false);
  const [showBB, setShowBB] = useState(false);

  // Allow external control of symbol via keyboard shortcut
  useEffect(() => {
    if (chartSymbolIndex !== undefined && watchlist[chartSymbolIndex]) {
      setSymbol(watchlist[chartSymbolIndex]);
    }
  }, [chartSymbolIndex, watchlist]);

  const { data: candles } = usePolling<Candle[]>(`/api/candles/${symbol}?timeframe=${timeframe}`, 2000);
  const { data: indicators } = usePolling<Indicators>(
    (showEMA || showBB) ? `/api/indicators/${symbol}?timeframe=${timeframe}` : "",
    (showEMA || showBB) ? 2000 : 999999
  );

  const displayCandles = candles || [];
  const lastCandle = displayCandles[displayCandles.length - 1];
  const sessionHigh = displayCandles.length > 0 ? Math.max(...displayCandles.map((c) => c.high)) : 0;
  const sessionLow = displayCandles.length > 0 ? Math.min(...displayCandles.map((c) => c.low)) : 0;

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
          >
            {watchlist.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          {lastCandle && (
            <span className={`font-mono text-lg font-bold ${lastCandle.close >= lastCandle.open ? "text-green-400" : "text-red-400"}`}>
              {formatCurrency(lastCandle.close)}
            </span>
          )}
          {displayCandles.length > 0 && (
            <div className="flex gap-3 text-xs text-gray-400 font-mono">
              <span>H: <span className="text-green-400">{formatCurrency(sessionHigh)}</span></span>
              <span>L: <span className="text-red-400">{formatCurrency(sessionLow)}</span></span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Indicator toggles */}
          <button
            onClick={() => setShowEMA(!showEMA)}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${showEMA ? "bg-blue-900/40 text-blue-400 border-blue-700" : "text-gray-500 border-gray-700 hover:text-gray-300"}`}
          >
            EMA
          </button>
          <button
            onClick={() => setShowBB(!showBB)}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${showBB ? "bg-purple-900/40 text-purple-400 border-purple-700" : "text-gray-500 border-gray-700 hover:text-gray-300"}`}
          >
            BB
          </button>
          {/* Timeframe toggles */}
          <div className="flex border border-gray-700 rounded overflow-hidden ml-2">
            <button
              onClick={() => setTimeframe("1m")}
              className={`text-xs px-2 py-0.5 ${timeframe === "1m" ? "bg-gray-600 text-white" : "text-gray-500 hover:text-gray-300"}`}
            >
              1m
            </button>
            <button
              onClick={() => setTimeframe("5m")}
              className={`text-xs px-2 py-0.5 ${timeframe === "5m" ? "bg-gray-600 text-white" : "text-gray-500 hover:text-gray-300"}`}
            >
              5m
            </button>
          </div>
        </div>
      </div>

      {displayCandles.length < 1 ? (
        <div className="h-[300px] flex items-center justify-center text-gray-500 text-sm">
          Waiting for candle data...
        </div>
      ) : (
        <CandleSVG candles={displayCandles} indicators={indicators} showEMA={showEMA} showBB={showBB} />
      )}
    </div>
  );
}

function CandleSVG({ candles, indicators, showEMA, showBB }: { candles: Candle[]; indicators: Indicators | null; showEMA: boolean; showBB: boolean }) {
  const width = 900;
  const height = 280;
  const padding = { top: 10, bottom: 20, left: 50, right: 10 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const allHigh = Math.max(...candles.map((c) => c.high));
  const allLow = Math.min(...candles.map((c) => c.low));
  const priceRange = allHigh - allLow || 1;

  const candleWidth = Math.max(2, (chartW / candles.length) * 0.7);
  const gap = (chartW / candles.length) * 0.3;

  const yScale = (price: number) => padding.top + chartH - ((price - allLow) / priceRange) * chartH;
  const xPos = (i: number) => padding.left + (i / candles.length) * chartW + gap / 2;
  const xCenter = (i: number) => xPos(i) + candleWidth / 2;

  const yLabels = 5;
  const yStep = priceRange / yLabels;

  // Build indicator polyline paths
  const buildLine = (values: (number | null)[]): string => {
    const points: string[] = [];
    for (let i = 0; i < values.length && i < candles.length; i++) {
      if (values[i] !== null) {
        points.push(`${xCenter(i)},${yScale(values[i]!)}`);
      }
    }
    return points.join(" ");
  };

  return (
    <div style={{ width: "100%", height: 300, overflow: "hidden" }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
        {/* Grid */}
        {Array.from({ length: yLabels + 1 }).map((_, i) => {
          const price = allLow + yStep * i;
          const y = yScale(price);
          return (
            <g key={i}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke="#374151" strokeDasharray="2,4" />
              <text x={padding.left - 5} y={y + 3} textAnchor="end" fill="#9ca3af" fontSize="9" fontFamily="monospace">₹{price.toFixed(0)}</text>
            </g>
          );
        })}

        {/* Bollinger Bands fill */}
        {showBB && indicators?.bb_upper && indicators?.bb_lower && (() => {
          const upperPts: string[] = [];
          const lowerPts: string[] = [];
          for (let i = 0; i < candles.length; i++) {
            const u = indicators.bb_upper[i];
            const l = indicators.bb_lower[i];
            if (u !== null && l !== null) {
              upperPts.push(`${xCenter(i)},${yScale(u)}`);
              lowerPts.push(`${xCenter(i)},${yScale(l)}`);
            }
          }
          if (upperPts.length < 2) return null;
          const polygon = [...upperPts, ...lowerPts.reverse()].join(" ");
          return <polygon points={polygon} fill="#a78bfa" opacity={0.05} />;
        })()}

        {/* Bollinger Bands lines */}
        {showBB && indicators && (
          <>
            <polyline points={buildLine(indicators.bb_upper)} fill="none" stroke="#f87171" strokeWidth="1" strokeDasharray="3,3" opacity={0.7} />
            <polyline points={buildLine(indicators.bb_middle)} fill="none" stroke="#9ca3af" strokeWidth="1" strokeDasharray="4,4" opacity={0.5} />
            <polyline points={buildLine(indicators.bb_lower)} fill="none" stroke="#4ade80" strokeWidth="1" strokeDasharray="3,3" opacity={0.7} />
          </>
        )}

        {/* Candles */}
        {candles.map((c, i) => {
          const x = xPos(i);
          const isGreen = c.close >= c.open;
          const bodyTop = yScale(Math.max(c.open, c.close));
          const bodyBot = yScale(Math.min(c.open, c.close));
          const bodyH = Math.max(1, bodyBot - bodyTop);
          const wickX = x + candleWidth / 2;
          return (
            <g key={i}>
              <line x1={wickX} x2={wickX} y1={yScale(c.high)} y2={yScale(c.low)} stroke={isGreen ? "#4ade80" : "#f87171"} strokeWidth={1} />
              <rect x={x} y={bodyTop} width={candleWidth} height={bodyH} fill={isGreen ? "#4ade80" : "#f87171"} opacity={c.in_progress ? 0.5 : 1} />
            </g>
          );
        })}

        {/* EMA lines */}
        {showEMA && indicators && (
          <>
            <polyline points={buildLine(indicators.ema_fast)} fill="none" stroke="#60a5fa" strokeWidth="1.5" />
            <polyline points={buildLine(indicators.ema_slow)} fill="none" stroke="#fb923c" strokeWidth="1.5" />
          </>
        )}

        {/* X-axis */}
        {candles.filter((_, i) => i % 10 === 0).map((c, idx) => {
          const i = idx * 10;
          return (
            <text key={i} x={xCenter(i)} y={height - 4} textAnchor="middle" fill="#9ca3af" fontSize="8" fontFamily="monospace">
              {formatCandleTime(c.timestamp)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

function formatCandleTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}
