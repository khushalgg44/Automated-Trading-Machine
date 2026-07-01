# AlgoTradeX — Algorithmic Paper Trading Platform

A real-time automated paper trading terminal that simulates algorithmic trading against live-like market data. Built as a B.Tech Computer Science major project, it demonstrates production-grade trading system architecture with event-driven design, multiple concurrent strategies, risk management, and a full React dashboard.

No real money is ever used. All trades are simulated against a virtual ₹10,00,000 portfolio.

## Screenshots

*Screenshots to be added*

## Features

### Trading Engine
- Real-time paper trading with simulated NSE market data (8 stocks)
- 3 automated strategies running concurrently (EMA Cross, RSI Mean Reversion, Bollinger Bands)
- Risk management chain with 3 validators (Capital, Max Positions, Daily Loss)
- Manual trade execution panel
- Interactive watchlist with add/remove (8 NSE stocks available)

### Charting & Visualization
- Live candlestick charts with custom SVG rendering
- EMA and Bollinger Band indicator overlays (toggle on/off)
- Multi-timeframe support (1-minute, 5-minute candles)
- Real-time equity curve
- Risk gauges and progress bars

### Backtesting
- Backtesting engine with real NSE historical data (Yahoo Finance)
- Strategy comparison — run all 3 strategies on same data, side-by-side results
- Overlaid equity curves for visual comparison
- Downloadable backtest results

### Analytics & Monitoring
- Performance analytics (win rate, profit factor, max drawdown, Sharpe-like metrics)
- Order tape (real-time order flow display)
- System health monitor (ticks/sec, memory, CPU, uptime)
- Structured logging with rotation
- 37 automated tests

### User Experience
- Command palette (Ctrl+K) with fuzzy search
- Keyboard shortcuts (D=Demo, T=Theme, 1/2/3=Chart symbols, R=Reset)
- Dark/Light theme toggle
- Demo mode for instant live presentations (10x speed)
- Session report generator (printable PDF via browser)
- Architecture documentation (built-in, accessible from command palette)
- Trade journal with annotations
- Data export (CSV trades, JSON analytics)
- Browser notifications for order rejections

### Integration
- Zerodha Kite Connect integration layer (ready, not active)
- OAuth flow implemented, WebSocket ticker with auto-reconnect
- Falls back to mock data when Zerodha token is unavailable

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn, Pydantic |
| Frontend | React 19, TypeScript, Tailwind CSS v4, Vite 8, Recharts |
| Testing | pytest (37 tests), pytest-asyncio |
| Data | In-memory + JSON persistence, Yahoo Finance (yfinance) |
| Monitoring | psutil, structured logging, RotatingFileHandler |
| External | Zerodha Kite Connect (optional) |

## Architecture

```
[Tick Source] → [PriceCache] → [Strategy Engine] → [Signal]
                                       ↓
[Dashboard] ← [EventBus] ← [Paper Engine] ← [Risk Manager]
```

**Design Patterns:**
- **Strategy Pattern** — interchangeable trading algorithms (`app/core/strategy/`)
- **Chain of Responsibility** — independent, reorderable risk validators (`app/core/risk/`)
- **Observer (Pub/Sub)** — decoupled event-driven communication (`app/event_bus.py`)
- **Factory** — dynamic strategy creation and lifecycle management (`app/core/strategy/registry.py`)
- **Repository Pattern** — swappable persistence layer (JSON now, Postgres-ready)

Full architecture docs available in the dashboard: Ctrl+K → "Architecture Docs"

## Quick Start

```bash
# Clone the repo
git clone <url>
cd algotradex

# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:5173
# Click "▶ Demo" to see it in action
```

## Running Tests

```bash
cd algotradex
pytest -v
# 37 tests: strategies, risk validators, portfolio, backtesting, smoke
```

## Backtesting with Real Data

```bash
# Download 6 months of NSE historical data
python scripts/download_data.py

# Then use the Backtesting panel in the dashboard
# Or compare all strategies: Ctrl+K → "Run Backtest"
```

## Zerodha Integration (Optional)

Requires a Zerodha account + Kite Connect subscription.

```bash
# Set environment variables
export ALGOTRADEX_DATA_SOURCE=zerodha
export ALGOTRADEX_ZERODHA_API_KEY=your_api_key
export ALGOTRADEX_ZERODHA_API_SECRET=your_api_secret

# Start the server — it will prompt for OAuth login via the dashboard
uvicorn app.main:app --reload
```

Falls back to mock data automatically if token is expired or missing.

## Project Structure

```
algotradex/
├── app/
│   ├── main.py                 # FastAPI app + all endpoints
│   ├── config.py               # Settings (Pydantic, env vars)
│   ├── event_bus.py            # Async pub/sub + event types
│   └── core/
│       ├── market/             # PriceCache, MockTickGenerator, CandleAggregator, Watchlist
│       ├── strategy/           # BaseStrategy, EMA Cross, RSI, Bollinger Bands, Registry
│       ├── trading/            # PaperEngine, OrderManager, PortfolioManager, OrderLog
│       ├── risk/               # RiskManager + 3 validators
│       ├── backtest/           # BacktestEngine, DataLoader
│       ├── auth/               # Zerodha OAuth helpers
│       ├── analytics.py        # Performance metric computation
│       └── logger.py           # Structured logging setup
├── frontend/
│   └── src/
│       ├── App.tsx             # Main layout + keyboard shortcuts
│       ├── components/         # 18 React components
│       ├── hooks/              # usePolling, useTheme
│       ├── types.ts            # TypeScript interfaces
│       └── utils.ts            # Currency formatting
├── data/                       # Historical CSV files (Yahoo Finance)
├── tests/                      # 37 pytest tests
├── scripts/                    # Data download script
├── logs/                       # Rotating log files (auto-created)
├── requirements.txt
└── README.md
```

## Design Decisions

- **Mock data first, real data swap-in** — PriceCache abstraction means downstream code never knows if data is real or simulated
- **In-memory over Postgres** — speed of development; architecture supports Postgres swap via Repository pattern
- **Decimal everywhere** — financial precision guaranteed, never use float for money
- **Event-driven architecture** — components are decoupled via pub/sub, easy to add new consumers
- **Strategies only emit signals** — they never touch orders directly; separation of concerns
- **Risk chain is short-circuit** — first failure blocks immediately, remaining validators skipped

## Future Enhancements

- PostgreSQL + Alembic migrations for persistent storage
- Additional strategies (VWAP, MACD, Supertrend)
- Multi-user support with authentication
- Telegram/Discord notification bot
- CI/CD pipeline with GitHub Actions
- Docker containerization
- Machine learning signal enhancement
- Options strategy support

## Author

**Khushal Garg** — B.Tech Computer Science, Major Project 2026

## License

MIT
