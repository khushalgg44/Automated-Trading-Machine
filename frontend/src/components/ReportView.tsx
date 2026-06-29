import { useState } from "react";
import { formatCurrency } from "../utils";

interface ReportData {
  generated_at: string;
  session_start: string;
  data_source: string;
  portfolio: { capital_available: number; initial_capital: number; positions_count: number; total_trades: number };
  positions: any[];
  analytics: Record<string, string>;
  strategies: { name: string; active: boolean; config: Record<string, number>; signals_generated: number }[];
  risk_summary: { total_rejections: number };
  session: { total_ticks: number; total_events: number };
  top_trades: any[];
  bottom_trades: any[];
  total_trades: number;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function ReportView({ isOpen, onClose }: Props) {
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/report/summary");
      const json = await res.json();
      setData(json);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-white text-black overflow-y-auto print:static">
      <div className="max-w-4xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 no-print">
          <button onClick={onClose} className="px-3 py-1 bg-gray-200 rounded text-sm hover:bg-gray-300">← Back to Dashboard</button>
          <div className="flex gap-2">
            {!data && <button onClick={generate} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded font-bold text-sm disabled:opacity-50">{loading ? "Generating..." : "Generate Report"}</button>}
            {data && <button onClick={() => window.print()} className="px-4 py-2 bg-green-600 text-white rounded font-bold text-sm">🖨️ Print / Save PDF</button>}
          </div>
        </div>

        {!data ? (
          <div className="text-center py-20 text-gray-500">
            <h2 className="text-2xl font-bold mb-2">Session Report</h2>
            <p>Click "Generate Report" to create a summary of this trading session.</p>
          </div>
        ) : (
          <div>
            <h1 className="text-3xl font-bold text-center mb-1">AlgoTradeX — Paper Trading Session Report</h1>
            <p className="text-center text-gray-500 text-sm mb-8">Generated: {new Date(data.generated_at).toLocaleString("en-IN")} • Data Source: {data.data_source.toUpperCase()}</p>

            {/* Portfolio Summary */}
            <section className="mb-6">
              <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-3">Portfolio Summary</h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-gray-500">Initial Capital:</span> <strong>{formatCurrency(data.portfolio.initial_capital)}</strong></div>
                <div><span className="text-gray-500">Cash Available:</span> <strong>{formatCurrency(data.portfolio.capital_available)}</strong></div>
                <div><span className="text-gray-500">Open Positions:</span> <strong>{data.portfolio.positions_count}</strong></div>
                <div><span className="text-gray-500">Total Trades:</span> <strong>{data.total_trades}</strong></div>
              </div>
            </section>

            {/* Analytics */}
            <section className="mb-6">
              <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-3">Trade Statistics</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                <div><span className="text-gray-500">Win Rate:</span> <strong>{data.analytics.win_rate}%</strong></div>
                <div><span className="text-gray-500">Profit Factor:</span> <strong>{data.analytics.profit_factor}</strong></div>
                <div><span className="text-gray-500">Avg Profit:</span> <strong className="text-green-600">₹{data.analytics.avg_profit}</strong></div>
                <div><span className="text-gray-500">Avg Loss:</span> <strong className="text-red-600">₹{data.analytics.avg_loss}</strong></div>
                <div><span className="text-gray-500">Max Drawdown:</span> <strong className="text-red-600">₹{data.analytics.max_drawdown}</strong></div>
                <div><span className="text-gray-500">Best Trade:</span> <strong className="text-green-600">₹{data.analytics.best_trade}</strong></div>
                <div><span className="text-gray-500">Worst Trade:</span> <strong className="text-red-600">₹{data.analytics.worst_trade}</strong></div>
                <div><span className="text-gray-500">Rejections:</span> <strong>{data.risk_summary.total_rejections}</strong></div>
              </div>
            </section>

            {/* Strategies */}
            <section className="mb-6">
              <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-3">Strategy Performance</h2>
              <table className="w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-1">Strategy</th><th className="text-left py-1">Status</th><th className="text-left py-1">Config</th><th className="text-right py-1">Signals</th></tr></thead>
                <tbody>
                  {data.strategies.map((s) => (
                    <tr key={s.name} className="border-b border-gray-100">
                      <td className="py-1 font-medium">{s.name}</td>
                      <td className="py-1">{s.active ? "🟢 Running" : "⚪ Stopped"}</td>
                      <td className="py-1 text-gray-500 text-xs">{JSON.stringify(s.config)}</td>
                      <td className="py-1 text-right">{s.signals_generated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {/* Top/Bottom Trades */}
            {data.top_trades.length > 0 && (
              <section className="mb-6">
                <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-3">Notable Trades</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="font-bold text-green-700 text-sm mb-1">Best Trades</h3>
                    {data.top_trades.map((t: any) => (
                      <p key={t.id} className="text-xs text-gray-600">{t.symbol} {t.direction} x{t.qty} — P&L: <strong className="text-green-600">₹{t.pnl}</strong></p>
                    ))}
                  </div>
                  <div>
                    <h3 className="font-bold text-red-700 text-sm mb-1">Worst Trades</h3>
                    {data.bottom_trades.map((t: any) => (
                      <p key={t.id} className="text-xs text-gray-600">{t.symbol} {t.direction} x{t.qty} — P&L: <strong className="text-red-600">₹{t.pnl}</strong></p>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* Session Info */}
            <section className="mb-6">
              <h2 className="text-lg font-bold border-b border-gray-300 pb-1 mb-3">Session Info</h2>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-gray-500">Session Start:</span> <strong>{new Date(data.session_start).toLocaleString("en-IN")}</strong></div>
                <div><span className="text-gray-500">Total Ticks:</span> <strong>{data.session.total_ticks.toLocaleString()}</strong></div>
                <div><span className="text-gray-500">Total Events:</span> <strong>{data.session.total_events.toLocaleString()}</strong></div>
              </div>
            </section>

            <footer className="text-center text-xs text-gray-400 mt-8 pt-4 border-t">
              AlgoTradeX Paper Trading Terminal — Auto-generated report. No real money involved.
            </footer>
          </div>
        )}
      </div>
    </div>
  );
}
