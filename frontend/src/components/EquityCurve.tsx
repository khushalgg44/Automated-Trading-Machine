import { useEffect, useRef, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Area, AreaChart } from "recharts";
import { Prices, Portfolio, Position } from "../types";

interface DataPoint {
  time: string;
  equity: number;
}

const MAX_POINTS = 150;

interface Props {
  prices: Prices | null;
}

export default function EquityCurve({ prices }: Props) {
  const [data, setData] = useState<DataPoint[]>([]);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    const fetchEquity = async () => {
      try {
        const [portfolioRes, positionsRes] = await Promise.all([
          fetch("/api/portfolio"),
          fetch("/api/positions"),
        ]);

        if (!portfolioRes.ok || !positionsRes.ok) return;

        const portfolio: Portfolio = await portfolioRes.json();
        const positions: Position[] = await positionsRes.json();

        // Equity = cash + sum(qty * current_price) for all positions
        let positionValue = 0;
        for (const pos of positions) {
          const cmp = prices?.[pos.symbol];
          if (cmp) {
            positionValue += pos.qty * cmp;
          } else {
            // Fallback: use avg_price if no live price yet
            positionValue += pos.qty * pos.avg_price;
          }
        }

        const equity = portfolio.capital_available + positionValue;
        const now = new Date();
        const time = now.toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });

        setData((prev) => {
          const next = [...prev, { time, equity }];
          if (next.length > MAX_POINTS) {
            return next.slice(next.length - MAX_POINTS);
          }
          return next;
        });
      } catch {
        // Silently skip on error
      }
    };

    fetchEquity();
    intervalRef.current = window.setInterval(fetchEquity, 2000);

    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
  }, [prices]);

  if (data.length < 2) {
    return (
      <div className="bg-gray-800 rounded-lg p-5 border border-gray-700 h-[200px] flex items-center justify-center">
        <p className="text-gray-500 text-sm">Building equity curve...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 mb-2 uppercase tracking-wide">
        Equity Curve
      </h2>
      <div style={{ width: "100%", height: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
            <XAxis
              dataKey="time"
              tick={{ fill: "#9ca3af", fontSize: 10 }}
              axisLine={{ stroke: "#374151" }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: "#9ca3af", fontSize: 10 }}
              axisLine={{ stroke: "#374151" }}
              tickLine={false}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => `₹${(v / 100000).toFixed(1)}L`}
              width={55}
            />
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4ade80" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#4ade80"
              strokeWidth={2}
              fill="url(#equityGradient)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
