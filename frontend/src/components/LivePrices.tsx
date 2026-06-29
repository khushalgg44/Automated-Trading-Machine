import { Prices } from "../types";
import { formatCurrency } from "../utils";

interface Props {
  prices: Prices | null;
  loading: boolean;
  error: string | null;
}

export default function LivePrices({ prices, loading, error }: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">
        Live Prices
      </h2>
      {loading ? (
        <p className="text-gray-500 text-sm">Connecting...</p>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : !prices || Object.keys(prices).length === 0 ? (
        <p className="text-gray-500 text-sm">Waiting for ticks...</p>
      ) : (
        <div className="space-y-3">
          {Object.entries(prices).map(([symbol, price]) => (
            <div
              key={symbol}
              className="flex items-center justify-between py-2 px-3 bg-gray-900/50 rounded"
            >
              <span className="font-medium text-white">{symbol}</span>
              <span className="font-mono text-lg text-green-400">
                {formatCurrency(price)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
