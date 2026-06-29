import { useState, useEffect, useRef } from "react";
import { usePolling } from "../hooks/usePolling";
import { formatCurrency } from "../utils";

interface Order {
  id: number;
  timestamp: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  status: "FILLED" | "REJECTED";
  strategy: string;
  rejection_reason: string | null;
}

export default function OrderTape() {
  const [expanded, setExpanded] = useState(false);
  const { data } = usePolling<Order[]>("/api/order-book", 2000);
  const scrollRef = useRef<HTMLDivElement>(null);

  const orders = data ? [...data].reverse().slice(0, 50) : [];

  useEffect(() => {
    if (scrollRef.current && expanded) {
      scrollRef.current.scrollTop = 0;
    }
  }, [data, expanded]);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Collapse header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-700/50 transition-colors"
      >
        <span className="font-medium uppercase tracking-wide">Order Tape</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div ref={scrollRef} className="max-h-48 overflow-y-auto px-2 pb-2">
          {orders.length === 0 ? (
            <p className="text-gray-500 text-xs px-2 py-2">No orders yet</p>
          ) : (
            <div className="space-y-px">
              {orders.map((order) => (
                <div
                  key={order.id}
                  className={`flex items-center gap-2 px-2 py-0.5 text-xs font-mono rounded ${
                    order.status === "REJECTED" ? "opacity-50" : ""
                  }`}
                  title={order.rejection_reason || undefined}
                >
                  <span className="text-gray-500 w-14 shrink-0">
                    {formatTime(order.timestamp)}
                  </span>
                  <span className="text-white w-16 shrink-0">{order.symbol}</span>
                  <span
                    className={`w-8 shrink-0 font-bold ${
                      order.status === "REJECTED"
                        ? "text-gray-500 line-through"
                        : order.side === "BUY"
                        ? "text-green-400"
                        : "text-red-400"
                    }`}
                  >
                    {order.side}
                  </span>
                  <span className="text-gray-300 w-8 shrink-0 text-right">{order.quantity}</span>
                  <span className="text-gray-300 w-20 shrink-0 text-right">
                    {formatCurrency(order.price)}
                  </span>
                  <span
                    className={`text-xs ${
                      order.status === "FILLED" ? "text-green-600" : "text-red-500"
                    }`}
                  >
                    {order.status === "REJECTED" ? "✗" : "✓"}
                  </span>
                  {order.rejection_reason && (
                    <span className="text-red-400 truncate text-xs ml-1" title={order.rejection_reason}>
                      {order.rejection_reason.slice(0, 30)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch { return iso; }
}
