import { useState } from "react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function ArchitectureDocs({ isOpen, onClose }: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-white text-black overflow-y-auto print:static">
      <div className="max-w-4xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8 no-print">
          <button onClick={onClose} className="px-3 py-1 bg-gray-200 rounded text-sm hover:bg-gray-300">← Back</button>
          <button onClick={() => window.print()} className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-bold">🖨️ Print</button>
        </div>

        <h1 className="text-3xl font-bold text-center mb-2">AlgoTradeX — System Architecture</h1>
        <p className="text-center text-gray-500 text-sm mb-10">Automated Paper Trading Platform • Technical Documentation</p>

        {/* Section 1: System Overview */}
        <Section title="1. System Overview">
          <div className="bg-gray-50 border rounded-lg p-6 font-mono text-xs leading-relaxed mb-4 overflow-x-auto">
            <pre className="text-gray-700">{`
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│  [Mock Generator / Zerodha WebSocket] → [EventBus: TICK_RECEIVED]│
│                              ↓                                   │
│  [PriceCache] ← updates on every tick                           │
│  [CandleAggregator] ← aggregates into 1m/5m OHLC               │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      STRATEGY ENGINE                             │
│  [EMA Cross] [RSI Mean Reversion] [Bollinger Bands]             │
│       ↓              ↓                    ↓                     │
│  Subscribes to TICK_RECEIVED → computes indicators              │
│  Generates SIGNAL (BUY/SELL) → publishes SIGNAL_GENERATED       │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                     EXECUTION PIPELINE                            │
│  [Order Manager] ← subscribes to SIGNAL_GENERATED               │
│        ↓                                                         │
│  [Risk Manager] ← Chain: Capital → Positions → DailyLoss        │
│        ↓ (approved)                                              │
│  [Paper Engine] ← fills at PriceCache LTP                       │
│        ↓                                                         │
│  [Portfolio Manager] ← updates capital, positions, trades        │
│        ↓                                                         │
│  [EventBus: ORDER_FILLED] → Dashboard updates                   │
└─────────────────────────────────────────────────────────────────┘
            `}</pre>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Component name="EventBus" desc="Async pub/sub system. All components communicate through events, never directly." />
            <Component name="PriceCache" desc="In-memory latest price for each symbol. Updated on every tick." />
            <Component name="CandleAggregator" desc="Converts raw ticks into 1m and 5m OHLC candles for charting." />
            <Component name="Strategy Engine" desc="Pluggable trading algorithms. Each subscribes to ticks independently." />
            <Component name="Risk Manager" desc="Chain of validators that must ALL approve before order execution." />
            <Component name="Paper Engine" desc="Simulates order fills at current market price. No real orders." />
            <Component name="Portfolio Manager" desc="Tracks capital, positions, trades. Persists to JSON file." />
            <Component name="Order Log" desc="Records all orders (filled + rejected) for the order tape display." />
          </div>
        </Section>

        {/* Section 2: Design Patterns */}
        <Section title="2. Design Patterns Used">
          <div className="space-y-3 text-sm">
            <Pattern name="Strategy Pattern" location="app/core/strategy/" desc="Interchangeable trading algorithms sharing a common BaseStrategy interface. New strategies drop in without modifying existing code." />
            <Pattern name="Chain of Responsibility" location="app/core/risk/" desc="Independent validators run in sequence. First rejection short-circuits — remaining validators are skipped." />
            <Pattern name="Observer (Pub/Sub)" location="app/event_bus.py" desc="Decoupled communication. Publishers don't know who subscribes. Strategies, risk, UI all react to events independently." />
            <Pattern name="Factory" location="app/core/strategy/registry.py" desc="Dynamic strategy creation and lifecycle management. Registry creates, starts, stops strategies by name." />
            <Pattern name="Singleton" location="All managers" desc="Single instances shared across the app — PriceCache, PortfolioManager, EventBus ensure consistent state." />
            <Pattern name="Repository Pattern" location="app/core/trading/portfolio_manager.py" desc="Swappable persistence layer. Currently JSON file, designed for Postgres upgrade without changing business logic." />
          </div>
        </Section>

        {/* Section 3: API Reference */}
        <Section title="3. API Reference">
          <div className="space-y-4 text-sm">
            <ApiGroup title="Market Data" endpoints={[
              ["GET", "/prices", "Current prices for all universe stocks"],
              ["GET", "/candles/{symbol}", "OHLC candles (1m or 5m timeframe)"],
              ["GET", "/indicators/{symbol}", "EMA and Bollinger Band overlay data"],
              ["GET", "/watchlist", "Current watchlist symbols"],
              ["POST", "/watchlist", "Add symbol to watchlist"],
              ["DELETE", "/watchlist/{symbol}", "Remove from watchlist"],
              ["GET", "/universe", "All available symbols"],
            ]} />
            <ApiGroup title="Trading" endpoints={[
              ["GET", "/portfolio", "Portfolio summary (capital, positions count)"],
              ["GET", "/positions", "All open positions with P&L"],
              ["GET", "/trades", "Trade history with notes"],
              ["POST", "/manual-trade", "Execute a manual paper trade"],
              ["PUT", "/trade/{id}/note", "Add/update a trade note"],
              ["POST", "/reset-portfolio", "Reset to initial capital"],
              ["GET", "/order-book", "Last 100 orders (filled + rejected)"],
            ]} />
            <ApiGroup title="Strategies" endpoints={[
              ["GET", "/strategies", "List all strategies with config"],
              ["POST", "/strategy/{name}/start", "Start a strategy"],
              ["POST", "/strategy/{name}/stop", "Stop a strategy"],
              ["GET", "/strategy/{name}/config", "Get strategy parameters"],
              ["PUT", "/strategy/{name}/config", "Update parameters live"],
            ]} />
            <ApiGroup title="Analytics & Backtest" endpoints={[
              ["GET", "/analytics", "Performance metrics (win rate, PF, drawdown)"],
              ["POST", "/backtest", "Run single-strategy backtest"],
              ["POST", "/backtest/compare", "Compare multiple strategies"],
              ["GET", "/backtest/files", "Available CSV data files"],
              ["GET", "/session-stats", "Live session statistics"],
              ["GET", "/risk-status", "Current risk gauge state"],
            ]} />
            <ApiGroup title="System" endpoints={[
              ["GET", "/health", "System health (uptime, ticks/sec, memory)"],
              ["GET", "/events", "Recent event bus log"],
              ["GET", "/logs/recent", "Last 100 log lines"],
              ["GET", "/report/summary", "Full session report data"],
              ["GET", "/export/trades", "Download trades CSV"],
              ["GET", "/export/analytics", "Export analytics JSON"],
              ["GET", "/auth/zerodha/status", "Zerodha connection status"],
            ]} />
          </div>
        </Section>

        {/* Section 4: Tech Stack */}
        <Section title="4. Tech Stack">
          <div className="grid grid-cols-2 gap-6 text-sm">
            <div>
              <h4 className="font-bold mb-2">Backend</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• Python 3.12 + FastAPI + uvicorn</li>
                <li>• Pydantic for validation</li>
                <li>• Decimal for all financial math</li>
                <li>• asyncio event-driven architecture</li>
                <li>• Logging with RotatingFileHandler</li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-2">Frontend</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• React 19 + TypeScript</li>
                <li>• Tailwind CSS v4 (dark/light themes)</li>
                <li>• Vite build tool</li>
                <li>• Recharts for equity curves</li>
                <li>• Custom SVG candlestick chart</li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-2">Data</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• In-memory state + JSON persistence</li>
                <li>• Yahoo Finance historical data (yfinance)</li>
                <li>• Synthetic random-walk tick generator</li>
                <li>• Designed for Postgres upgrade path</li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-2">External</h4>
              <ul className="space-y-1 text-gray-600">
                <li>• Zerodha Kite Connect (ready, not active)</li>
                <li>• OAuth 2.0 token flow implemented</li>
                <li>• WebSocket ticker with auto-reconnect</li>
                <li>• psutil for system monitoring</li>
              </ul>
            </div>
          </div>
        </Section>

        <footer className="text-center text-xs text-gray-400 mt-8 pt-4 border-t">
          AlgoTradeX Paper Trading Terminal — Architecture Documentation
        </footer>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-xl font-bold border-b-2 border-gray-200 pb-2 mb-4">{title}</h2>
      {children}
    </section>
  );
}

function Component({ name, desc }: { name: string; desc: string }) {
  return (
    <div className="p-2 bg-gray-50 rounded border">
      <span className="font-bold text-sm">{name}</span>
      <p className="text-xs text-gray-600 mt-0.5">{desc}</p>
    </div>
  );
}

function Pattern({ name, location, desc }: { name: string; location: string; desc: string }) {
  return (
    <div className="flex gap-3 p-2 bg-gray-50 rounded border">
      <div className="flex-1">
        <span className="font-bold">{name}</span>
        <span className="text-xs text-gray-400 ml-2">{location}</span>
        <p className="text-xs text-gray-600 mt-0.5">{desc}</p>
      </div>
    </div>
  );
}

function ApiGroup({ title, endpoints }: { title: string; endpoints: string[][] }) {
  return (
    <div>
      <h4 className="font-bold text-gray-700 mb-1">{title}</h4>
      <table className="w-full text-xs">
        <tbody>
          {endpoints.map(([method, path, desc]) => (
            <tr key={path} className="border-b border-gray-100">
              <td className="py-0.5 w-12 font-mono font-bold text-blue-600">{method}</td>
              <td className="py-0.5 w-48 font-mono text-gray-700">{path}</td>
              <td className="py-0.5 text-gray-500">{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
