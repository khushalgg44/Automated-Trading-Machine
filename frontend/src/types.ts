/** API response types matching the FastAPI backend */

export interface Portfolio {
  capital_available: number;
  initial_capital: number;
  positions_count: number;
  total_trades: number;
}

export interface Position {
  symbol: string;
  qty: number;
  avg_price: number;
}

export interface Trade {
  id: number;
  symbol: string;
  direction: "BUY" | "SELL";
  qty: number;
  price: number;
  value: number;
  pnl: number;
  strategy: string;
  timestamp: string;
  note: string | null;
}

export interface Strategy {
  name: string;
  active: boolean;
  config: Record<string, number>;
}

export interface HealthStatus {
  status: string;
  generator_running: boolean;
}

export type Prices = Record<string, number>;
