import { useState, useRef, useEffect } from "react";
import { usePolling } from "../hooks/usePolling";

interface HealthData {
  status: string;
  generator_running: boolean;
  uptime_seconds: number;
  ticks_per_second: number;
  total_ticks_processed: number;
  total_events_published: number;
  last_tick_time: string | null;
  active_strategies: number;
  open_positions: number;
  memory_usage_mb: number | null;
  cpu_percent: number | null;
}

export default function SystemHealth() {
  const [expanded, setExpanded] = useState(false);
  const { data } = usePolling<HealthData>("/api/health", 3000);
  const [tpsHistory, setTpsHistory] = useState<number[]>([]);
  const prevTps = useRef<number>(0);

  // Track TPS sparkline data
  useEffect(() => {
    if (data) {
      setTpsHistory((prev) => {
        const next = [...prev, data.ticks_per_second];
        return next.slice(-30);
      });
      prevTps.current = data.ticks_per_second;
    }
  }, [data]);

  if (!data) return null;

  const isStalled = data.ticks_per_second === 0 && !data.generator_running;
  const isZerodhaIdle = isStalled && data.total_ticks_processed > 0; // Had ticks before, now idle (market closed)
  const statusColor = isStalled ? (isZerodhaIdle ? "bg-blue-400" : "bg-yellow-400") : "bg-green-400";
  const statusText = isStalled ? (isZerodhaIdle ? "IDLE" : "STALLED") : "OK";

  return (
    <div className="fixed bottom-20 right-4 z-40">
      {/* Collapsed view */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs text-gray-400 hover:text-white transition-colors shadow-lg"
      >
        <span className={`w-2 h-2 rounded-full ${statusColor} ${!isStalled ? "animate-pulse" : ""}`} />
        <span>System</span>
        <span className={isStalled ? "text-yellow-400" : "text-green-400"}>● {statusText}</span>
      </button>

      {/* Expanded panel */}
      {expanded && (
        <div className="mt-2 bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-xl min-w-[220px]">
          <div className="space-y-2 text-xs">
            <Row label="Uptime" value={formatUptime(data.uptime_seconds)} />
            <Row label="Ticks/sec" value={`${data.ticks_per_second}`} color={data.ticks_per_second > 0 ? "text-green-400" : "text-yellow-400"} />
            <Row label="Total Ticks" value={data.total_ticks_processed.toLocaleString()} />
            <Row label="Events" value={data.total_events_published.toLocaleString()} />
            {data.memory_usage_mb !== null && <Row label="Memory" value={`${data.memory_usage_mb} MB`} />}
            {data.cpu_percent !== null && <Row label="CPU" value={`${data.cpu_percent}%`} />}
            <Row label="Positions" value={String(data.open_positions)} />
            <Row label="Last Tick" value={data.last_tick_time ? formatTime(data.last_tick_time) : "—"} />

            {/* Sparkline */}
            {tpsHistory.length > 1 && (
              <div className="pt-1">
                <span className="text-gray-500">Tick Rate:</span>
                <Sparkline data={tpsHistory} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, color = "text-gray-300" }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className={`font-mono ${color}`}>{value}</span>
    </div>
  );
}

function Sparkline({ data }: { data: number[] }) {
  const width = 160;
  const height = 30;
  const max = Math.max(...data, 1);

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - (v / max) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="mt-1">
      <polyline
        points={points}
        fill="none"
        stroke="#4ade80"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch { return iso; }
}
