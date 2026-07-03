import { useState } from "react";
import { usePolling } from "../hooks/usePolling";
import { Trade } from "../types";

export default function PnLCalendar() {
  const { data: trades } = usePolling<Trade[]>("/api/trades", 5000);
  const [currentDate, setCurrentDate] = useState(new Date());

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Group trades by date and sum P&L
  const pnlByDate: Record<string, number> = {};
  if (trades) {
    for (const trade of trades) {
      if (trade.pnl && trade.pnl !== 0) {
        const dateStr = trade.timestamp.split("T")[0];
        pnlByDate[dateStr] = (pnlByDate[dateStr] || 0) + trade.pnl;
      }
    }
  }

  // Calendar generation
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const monthName = currentDate.toLocaleString("default", { month: "long" });

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));

  const days: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) days.push(null);
  for (let d = 1; d <= daysInMonth; d++) days.push(d);

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          P&L Calendar
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={prevMonth}
            className="text-gray-400 hover:text-white text-sm px-1"
          >
            ◀
          </button>
          <span className="text-sm text-gray-300 font-medium min-w-[120px] text-center">
            {monthName} {year}
          </span>
          <button
            onClick={nextMonth}
            className="text-gray-400 hover:text-white text-sm px-1"
          >
            ▶
          </button>
        </div>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d} className="text-center text-xs text-gray-500 py-0.5">
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {days.map((day, idx) => {
          if (day === null) {
            return <div key={`empty-${idx}`} className="h-10" />;
          }

          const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
          const pnl = pnlByDate[dateStr];
          const hasPnl = pnl !== undefined;

          let bgClass = "bg-gray-700/30";
          let textClass = "text-gray-500";

          if (hasPnl && pnl > 0) {
            bgClass = "bg-green-900/50 border border-green-700/50";
            textClass = "text-green-400";
          } else if (hasPnl && pnl < 0) {
            bgClass = "bg-red-900/50 border border-red-700/50";
            textClass = "text-red-400";
          }

          return (
            <div
              key={dateStr}
              className={`h-10 rounded flex flex-col items-center justify-center ${bgClass}`}
              title={hasPnl ? `₹${pnl.toFixed(2)}` : "No trades"}
            >
              <span className="text-xs text-gray-400">{day}</span>
              {hasPnl && (
                <span className={`text-[10px] font-mono ${textClass}`}>
                  {pnl > 0 ? "+" : ""}
                  {Math.abs(pnl) >= 1000
                    ? `${(pnl / 1000).toFixed(1)}k`
                    : pnl.toFixed(0)}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
