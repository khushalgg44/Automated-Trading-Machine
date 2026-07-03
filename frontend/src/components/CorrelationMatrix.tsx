import { useState } from "react";
import { usePolling } from "../hooks/usePolling";

interface CorrelationData {
  symbols: string[];
  matrix: number[][];
}

export default function CorrelationMatrix() {
  const [expanded, setExpanded] = useState(false);
  const { data } = usePolling<CorrelationData>("/api/correlation", 10000);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-700/50 transition-colors"
      >
        <span className="font-medium uppercase tracking-wide">Correlation Matrix</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="p-3 overflow-x-auto">
          {!data || data.symbols.length < 2 ? (
            <p className="text-gray-500 text-xs px-2 py-2">
              Waiting for price data (need at least 2 symbols with history)...
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="p-1 text-left text-gray-500" />
                  {data.symbols.map((sym) => (
                    <th key={sym} className="p-1 text-center text-gray-400 font-medium">
                      {sym.slice(0, 5)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.symbols.map((rowSym, i) => (
                  <tr key={rowSym}>
                    <td className="p-1 text-gray-400 font-medium">{rowSym.slice(0, 5)}</td>
                    {data.matrix[i].map((val, j) => {
                      const isPositive = val >= 0;
                      const magnitude = Math.abs(val);
                      const bgColor = isPositive
                        ? `rgba(34, 197, 94, ${magnitude * 0.5})`
                        : `rgba(239, 68, 68, ${magnitude * 0.5})`;

                      return (
                        <td
                          key={`${i}-${j}`}
                          className="p-1 text-center font-mono text-gray-200"
                          style={{ backgroundColor: bgColor }}
                        >
                          {val.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
