import { usePolling } from "../hooks/usePolling";
import { Position, Prices } from "../types";
import { formatCurrency } from "../utils";

interface Props {
  prices: Prices | null;
}

export default function PositionsTable({ prices }: Props) {
  const { data, error, loading } = usePolling<Position[]>("/api/positions", 2000);

  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">
        Active Positions
      </h2>
      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : !data || data.length === 0 ? (
        <p className="text-gray-500 text-sm">No open positions</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase border-b border-gray-700">
                <th className="text-left pb-2">Symbol</th>
                <th className="text-right pb-2">Qty</th>
                <th className="text-right pb-2">Avg Price</th>
                <th className="text-right pb-2">CMP</th>
                <th className="text-right pb-2">P&L</th>
                <th className="text-right pb-2">% Change</th>
              </tr>
            </thead>
            <tbody>
              {data.map((pos) => {
                const cmp = prices?.[pos.symbol] ?? null;
                const pnl = cmp ? (cmp - pos.avg_price) * pos.qty : null;
                const pctChange = cmp
                  ? ((cmp - pos.avg_price) / pos.avg_price) * 100
                  : null;

                return (
                  <tr
                    key={pos.symbol}
                    className="border-b border-gray-700/50 hover:bg-gray-700/30"
                  >
                    <td className="py-2 font-medium text-white">{pos.symbol}</td>
                    <td className="py-2 text-right font-mono">{pos.qty}</td>
                    <td className="py-2 text-right font-mono">
                      {formatCurrency(pos.avg_price)}
                    </td>
                    <td className="py-2 text-right font-mono">
                      {cmp ? formatCurrency(cmp) : "—"}
                    </td>
                    <td
                      className={`py-2 text-right font-mono font-semibold ${
                        pnl === null
                          ? "text-gray-500"
                          : pnl >= 0
                          ? "text-green-400"
                          : "text-red-400"
                      }`}
                    >
                      {pnl !== null ? formatCurrency(pnl) : "—"}
                    </td>
                    <td
                      className={`py-2 text-right font-mono ${
                        pctChange === null
                          ? "text-gray-500"
                          : pctChange >= 0
                          ? "text-green-400"
                          : "text-red-400"
                      }`}
                    >
                      {pctChange !== null ? `${pctChange >= 0 ? "+" : ""}${pctChange.toFixed(2)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
