"""FastAPI application — AlgoTradeX paper trading platform."""

import csv
import io
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.logger import get_logger, get_recent_logs

logger = get_logger("app.main")

# Import singletons to wire up event subscriptions
from app.core.market.mock_tick_generator import mock_tick_generator  # noqa: F401
from app.core.market.price_cache import price_cache  # noqa: F401
from app.core.market.watchlist import watchlist
from app.core.market.candle_aggregator import candle_aggregator  # noqa: F401
from app.core.trading.order_manager import order_manager  # noqa: F401
from app.core.trading.order_log import order_log
from app.core.trading.portfolio_manager import portfolio_manager
from app.core.trading.paper_engine import paper_engine
from app.core.risk.manager import risk_manager
from app.core.strategy.base_strategy import Signal
from app.core.strategy.registry import strategy_registry
from app.core.analytics import compute_analytics
from app.core.backtest.engine import run_backtest
from app.core.backtest.data_loader import load_csv
from app.event_bus import event_bus, Events
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    app.state.session_start = datetime.now().isoformat()
    app.state.data_source = settings.data_source

    # Choose data source
    if settings.data_source == "zerodha":
        from app.core.auth.zerodha_auth import load_token, is_token_valid
        token = load_token()
        if token and is_token_valid():
            from app.core.market.kite_connector import KiteTickerConnector
            app.state.kite_connector = KiteTickerConnector(
                settings.zerodha_api_key, token, settings.symbols
            )
            await app.state.kite_connector.start()
            logger.info("Zerodha Kite WebSocket started.")
        else:
            logger.warning("Zerodha token invalid/missing. Falling back to mock data.")
            app.state.data_source = "mock"
            await mock_tick_generator.start()
    else:
        await mock_tick_generator.start()

    await strategy_registry.start("ema_cross")
    await strategy_registry.start("rsi_mean_reversion")
    event_bus.log_custom(Events.STRATEGY_STARTED, "ema_cross")
    event_bus.log_custom(Events.STRATEGY_STARTED, "rsi_mean_reversion")
    print(f"[AlgoTradeX] Data source: {app.state.data_source}. Strategies active.")
    yield
    # Shutdown
    await strategy_registry.stop_all()
    if app.state.data_source == "zerodha" and hasattr(app.state, "kite_connector"):
        await app.state.kite_connector.stop()
    else:
        await mock_tick_generator.stop()
    print("[AlgoTradeX] Shutdown complete.")


app = FastAPI(
    title="AlgoTradeX",
    description="Automated paper-trading platform with mock market data",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── API Models ────────────────────────────────────────────────────────────────

class StrategyAction(BaseModel):
    name: str


class ManualTradeRequest(BaseModel):
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: int = 10


class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    file: str  # CSV filename in data/ folder


class BacktestCompareRequest(BaseModel):
    strategies: list[str]
    symbol: str
    file: str


class TradeNoteRequest(BaseModel):
    note: str


class StrategyConfigUpdate(BaseModel):
    fast_period: int | None = None
    slow_period: int | None = None
    period: int | None = None
    oversold: int | None = None
    overbought: int | None = None
    std_dev_multiplier: float | None = None


class WatchlistAddRequest(BaseModel):
    symbol: str


# ─── Strategy config metadata (for frontend display) ──────────────────────────

def _get_strategy_config(name: str) -> dict:
    """Get current live config from strategy instance."""
    s = strategy_registry.get(name)
    if not s:
        return {}
    if name == "ema_cross":
        return {"fast_period": s.fast_period, "slow_period": s.slow_period}
    if name == "rsi_mean_reversion":
        return {"period": s.period, "oversold": s.oversold, "overbought": s.overbought}
    if name == "bollinger_bands":
        return {"period": s.period, "std_dev": s.std_dev_multiplier}
    return {}


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/portfolio")
async def get_portfolio():
    """Current portfolio summary."""
    return portfolio_manager.get_portfolio_summary()


@app.get("/positions")
async def get_positions():
    """All open positions."""
    return portfolio_manager.get_positions()


@app.get("/trades")
async def get_trades():
    """Trade history."""
    return portfolio_manager.get_trades()


@app.get("/prices")
async def get_prices():
    """Current price cache (latest tick prices)."""
    return price_cache.get_all()


@app.post("/strategies/start")
async def start_strategy(body: StrategyAction):
    """Start a strategy by name."""
    success = await strategy_registry.start(body.name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy '{body.name}' not found")
    event_bus.log_custom(Events.STRATEGY_STARTED, body.name)
    return {"status": "started", "strategy": body.name}


@app.post("/strategies/stop")
async def stop_strategy(body: StrategyAction):
    """Stop a running strategy by name."""
    success = await strategy_registry.stop(body.name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy '{body.name}' not found")
    event_bus.log_custom(Events.STRATEGY_STOPPED, body.name)
    return {"status": "stopped", "strategy": body.name}


@app.post("/strategy/{strategy_name}/start")
async def start_strategy_by_path(strategy_name: str):
    """Start a strategy by path param."""
    success = await strategy_registry.start(strategy_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    event_bus.log_custom(Events.STRATEGY_STARTED, strategy_name)
    return {"status": "started", "strategy": strategy_name}


@app.post("/strategy/{strategy_name}/stop")
async def stop_strategy_by_path(strategy_name: str):
    """Stop a strategy by path param."""
    success = await strategy_registry.stop(strategy_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    event_bus.log_custom(Events.STRATEGY_STOPPED, strategy_name)
    return {"status": "stopped", "strategy": strategy_name}


@app.get("/strategies")
async def list_strategies():
    """List all registered strategies with config metadata."""
    names = strategy_registry.list_all()
    return [
        {
            "name": n,
            "active": strategy_registry.get(n).is_active,
            "config": _get_strategy_config(n),
        }
        for n in names
    ]


@app.get("/health")
async def health():
    """Detailed system health information."""
    import time
    tick_stats = event_bus.get_tick_stats()
    start = datetime.fromisoformat(app.state.session_start)
    uptime = (datetime.now() - start).total_seconds()

    # Memory usage
    memory_mb = None
    cpu_percent = None
    try:
        import psutil
        proc = psutil.Process()
        memory_mb = round(proc.memory_info().rss / 1024 / 1024, 1)
        cpu_percent = proc.cpu_percent(interval=None)
    except ImportError:
        import tracemalloc
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        current, peak = tracemalloc.get_traced_memory()
        memory_mb = round(current / 1024 / 1024, 1)

    return {
        "status": "ok",
        "generator_running": mock_tick_generator.is_running,
        "uptime_seconds": round(uptime),
        "ticks_per_second": tick_stats["ticks_per_second"],
        "total_ticks_processed": tick_stats["total_ticks"],
        "total_events_published": tick_stats["total_events"],
        "last_tick_time": tick_stats["last_tick_time"],
        "active_strategies": sum(1 for n in strategy_registry.list_all() if strategy_registry.get(n).is_active),
        "open_positions": len(portfolio_manager.positions),
        "memory_usage_mb": memory_mb,
        "cpu_percent": cpu_percent,
    }


@app.post("/manual-trade")
async def manual_trade(body: ManualTradeRequest):
    """Execute a manual paper trade — same pipeline as strategy signals."""
    side = body.side.upper()
    if side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")

    price = price_cache.get(body.symbol)
    if price is None:
        raise HTTPException(
            status_code=400,
            detail=f"No price available for {body.symbol}. Is the tick generator running?",
        )

    signal = Signal(
        direction=side,
        symbol=body.symbol,
        quantity=body.quantity,
        reason="Manual trade",
    )

    # Run through same risk checks
    approved, reason = risk_manager.check(signal)
    if not approved:
        event_bus.log_custom(Events.ORDER_REJECTED, f"[manual] Manual {side} {body.symbol} x{body.quantity}: {reason}")
        return {"status": "rejected", "reason": reason}

    # Execute via paper engine
    trade = await paper_engine.fill_order(signal, strategy="manual")
    if not trade:
        return {"status": "rejected", "reason": "Fill failed — no price"}

    return {"status": "filled", "trade": trade}


@app.post("/reset-portfolio")
async def reset_portfolio():
    """Reset portfolio to initial state. Strategies keep running."""
    portfolio_manager.reset()
    event_bus.clear_log()
    event_bus.log_custom(Events.PORTFOLIO_RESET, f"Portfolio reset to ₹{settings.initial_capital:,.2f}")
    return {"status": "reset", "capital": f"{settings.initial_capital:.2f}"}


@app.get("/events")
async def get_events():
    """Return the last 50 events from the event bus log."""
    return event_bus.get_recent_events(50)


@app.get("/analytics")
async def get_analytics():
    """Compute and return trading performance metrics."""
    trades = portfolio_manager.get_trades()
    return compute_analytics(trades, settings.initial_capital)


@app.post("/backtest")
async def run_backtest_endpoint(body: BacktestRequest):
    """Run a backtest with a strategy on historical CSV data."""
    # Validate strategy
    valid_strategies = ("ema_cross", "rsi_mean_reversion", "bollinger_bands")
    if body.strategy not in valid_strategies:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {body.strategy}")

    # Locate CSV file in data/ folder
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    filepath = os.path.join(data_dir, body.file)

    try:
        candles = load_csv(filepath)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CSV file not found: {body.file}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error loading CSV: {str(e)}")

    if not candles:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    # Run backtest (async, isolated from live system)
    try:
        results = await run_backtest(
            strategy_name=body.strategy,
            symbol=body.symbol,
            candles=candles,
            initial_capital=settings.initial_capital,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

    return results


@app.get("/backtest/files")
async def list_backtest_files():
    """List available CSV files in the data/ directory."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    if not os.path.exists(data_dir):
        return []
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    return files


@app.post("/backtest/compare")
async def compare_strategies(body: BacktestCompareRequest):
    """Run multiple strategies against the same data and compare results."""
    valid_strategies = ("ema_cross", "rsi_mean_reversion", "bollinger_bands")
    for s in body.strategies:
        if s not in valid_strategies:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {s}")

    # Load data once
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    filepath = os.path.join(data_dir, body.file)

    try:
        candles = load_csv(filepath)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CSV file not found: {body.file}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error loading CSV: {str(e)}")

    if not candles:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    # Run each strategy independently
    results = []
    for strategy_name in body.strategies:
        try:
            result = await run_backtest(
                strategy_name=strategy_name,
                symbol=body.symbol,
                candles=candles,
                initial_capital=settings.initial_capital,
            )
            results.append(result)
        except Exception as e:
            results.append({
                "strategy": strategy_name,
                "error": str(e),
            })

    return {"results": results}


# ─── Strategy Config Endpoints ─────────────────────────────────────────────────

@app.get("/strategy/{strategy_name}/config")
async def get_strategy_config(strategy_name: str):
    """Get current config for a strategy."""
    s = strategy_registry.get(strategy_name)
    if not s:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    return _get_strategy_config(strategy_name)


@app.put("/strategy/{strategy_name}/config")
async def update_strategy_config(strategy_name: str, body: StrategyConfigUpdate):
    """Update strategy parameters in place (no restart needed)."""
    s = strategy_registry.get(strategy_name)
    if not s:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

    errors: list[str] = []

    if strategy_name == "ema_cross":
        fast = body.fast_period if body.fast_period is not None else s.fast_period
        slow = body.slow_period if body.slow_period is not None else s.slow_period
        if not (2 <= fast <= 50):
            errors.append("fast_period must be between 2 and 50")
        if not (5 <= slow <= 200):
            errors.append("slow_period must be between 5 and 200")
        if fast >= slow:
            errors.append("fast_period must be less than slow_period")
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))
        s.fast_period = fast
        s.slow_period = slow

    elif strategy_name == "rsi_mean_reversion":
        period = body.period if body.period is not None else s.period
        oversold = body.oversold if body.oversold is not None else s.oversold
        overbought = body.overbought if body.overbought is not None else s.overbought
        if not (5 <= period <= 50):
            errors.append("period must be between 5 and 50")
        if not (10 <= oversold <= 40):
            errors.append("oversold must be between 10 and 40")
        if not (60 <= overbought <= 90):
            errors.append("overbought must be between 60 and 90")
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))
        s.period = period
        s.oversold = oversold
        s.overbought = overbought

    elif strategy_name == "bollinger_bands":
        period = body.period if body.period is not None else s.period
        std_dev = body.std_dev_multiplier if body.std_dev_multiplier is not None else s.std_dev_multiplier
        if not (5 <= period <= 50):
            errors.append("period must be between 5 and 50")
        if not (0.5 <= std_dev <= 4.0):
            errors.append("std_dev_multiplier must be between 0.5 and 4.0")
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))
        s.period = period
        s.std_dev_multiplier = std_dev

    else:
        raise HTTPException(status_code=400, detail=f"Config update not supported for '{strategy_name}'")

    event_bus.log_custom("STRATEGY_CONFIG_CHANGED", f"{strategy_name}: {_get_strategy_config(strategy_name)}")
    return _get_strategy_config(strategy_name)


# ─── Trade Notes Endpoint ──────────────────────────────────────────────────────

@app.put("/trade/{trade_id}/note")
async def set_trade_note(trade_id: int, body: TradeNoteRequest):
    """Add or update a note on a trade."""
    result = portfolio_manager.set_trade_note(trade_id, body.note)
    if not result:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    return result


# ─── Watchlist Endpoints ───────────────────────────────────────────────────────

@app.get("/watchlist")
async def get_watchlist():
    """Get current watchlist symbols."""
    return watchlist.symbols


@app.post("/watchlist")
async def add_to_watchlist(body: WatchlistAddRequest):
    """Add a symbol to the watchlist."""
    symbol = body.symbol.upper()
    if symbol not in settings.universe:
        raise HTTPException(status_code=400, detail=f"'{symbol}' is not in the available universe")
    success = watchlist.add(symbol)
    if not success:
        return {"status": "already_exists", "symbol": symbol}
    event_bus.log_custom("WATCHLIST_CHANGED", f"Added {symbol}")
    return {"status": "added", "symbol": symbol, "watchlist": watchlist.symbols}


@app.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove a symbol from the watchlist."""
    symbol = symbol.upper()
    success = watchlist.remove(symbol)
    if not success:
        raise HTTPException(status_code=404, detail=f"'{symbol}' not in watchlist")
    event_bus.log_custom("WATCHLIST_CHANGED", f"Removed {symbol}")
    return {"status": "removed", "symbol": symbol, "watchlist": watchlist.symbols}


@app.get("/universe")
async def get_universe():
    """Get all available symbols (full universe)."""
    return settings.universe


# ─── Session Stats Endpoint ────────────────────────────────────────────────────

@app.get("/session-stats")
async def get_session_stats():
    """Get session-level statistics."""
    all_events = event_bus.get_recent_events(200)
    total_signals = sum(1 for e in all_events if e["event"] == "SIGNAL_GENERATED")
    total_rejections = sum(1 for e in all_events if e["event"] == "ORDER_REJECTED")

    # Total PnL: realized (from trades) + unrealized (from open positions at current prices)
    trades = portfolio_manager.get_trades()
    realized_pnl = sum(t.get("pnl", 0) for t in trades if t.get("pnl"))

    unrealized_pnl = 0.0
    for pos in portfolio_manager.get_positions():
        cmp = price_cache.get(pos["symbol"])
        if cmp:
            unrealized_pnl += (cmp - pos["avg_price"]) * pos["qty"]

    active_count = sum(1 for n in strategy_registry.list_all() if strategy_registry.get(n).is_active)
    total_count = len(strategy_registry.list_all())

    return {
        "session_start": app.state.session_start,
        "total_pnl": round(realized_pnl + unrealized_pnl, 2),
        "todays_trades": len(trades),
        "total_signals": total_signals,
        "total_rejections": total_rejections,
        "active_strategy_count": active_count,
        "total_strategy_count": total_count,
    }


# ─── Export Endpoints ──────────────────────────────────────────────────────────

@app.get("/export/trades")
async def export_trades():
    """Export all trades as a downloadable CSV."""
    trades = portfolio_manager.get_trades()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Symbol", "Side", "Quantity", "Price", "Value", "Strategy", "PnL", "Note"])

    for t in trades:
        writer.writerow([
            t["id"], t["timestamp"], t["symbol"], t["direction"],
            t["qty"], t["price"], t["value"], t.get("strategy", ""),
            t.get("pnl", 0), t.get("note") or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=algotradex_trades.csv"},
    )


@app.get("/export/analytics")
async def export_analytics():
    """Export analytics as JSON (for reports)."""
    trades = portfolio_manager.get_trades()
    analytics = compute_analytics(trades, settings.initial_capital)
    analytics["export_timestamp"] = datetime.now().isoformat()
    analytics["total_trades_detail"] = len(trades)
    return analytics


# ─── Candlestick Data Endpoint ─────────────────────────────────────────────────

@app.get("/candles/{symbol}")
async def get_candles(symbol: str, timeframe: str = "1m"):
    """Return OHLC candles for a symbol."""
    symbol = symbol.upper()
    if timeframe not in ("1m", "5m"):
        timeframe = "1m"
    candles = candle_aggregator.get_candles(symbol, timeframe)
    if not candles:
        return []
    return candles


@app.get("/indicators/{symbol}")
async def get_indicators(symbol: str, timeframe: str = "1m"):
    """Return EMA and Bollinger Band overlay data for a symbol's candles."""
    symbol = symbol.upper()
    if timeframe not in ("1m", "5m"):
        timeframe = "1m"
    return candle_aggregator.get_indicators(symbol, timeframe)


# ─── Order Book / Tape Endpoint ────────────────────────────────────────────────

@app.get("/order-book")
async def get_order_book():
    """Return the last 100 orders (filled + rejected) in reverse chronological order."""
    return order_log.get_orders(100)


# ─── Risk Status Endpoint ──────────────────────────────────────────────────────

@app.get("/risk-status")
async def get_risk_status():
    """Return current risk state for gauge display."""
    from decimal import Decimal
    positions_used = len(portfolio_manager.positions)
    positions_max = settings.max_open_positions
    daily_loss_current = portfolio_manager.get_realized_daily_loss()
    daily_loss_max = float(Decimal(str(settings.max_daily_loss_pct)) * Decimal(str(settings.initial_capital)))
    capital_deployed = settings.initial_capital - portfolio_manager.capital
    capital_deployed_pct = (capital_deployed / settings.initial_capital) * 100 if settings.initial_capital > 0 else 0

    # Determine risk level
    pos_ratio = positions_used / positions_max if positions_max > 0 else 0
    loss_ratio = daily_loss_current / daily_loss_max if daily_loss_max > 0 else 0
    max_ratio = max(pos_ratio, loss_ratio, capital_deployed_pct / 100)

    if max_ratio >= 1.0:
        risk_level = "MAXED"
    elif max_ratio >= 0.8:
        risk_level = "HIGH"
    elif max_ratio >= 0.5:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "positions_used": positions_used,
        "positions_max": positions_max,
        "daily_loss_current": round(daily_loss_current, 2),
        "daily_loss_max": round(daily_loss_max, 2),
        "capital_deployed_percent": round(capital_deployed_pct, 1),
        "capital_available": round(portfolio_manager.capital, 2),
        "risk_level": risk_level,
    }


# ─── Zerodha Auth Endpoints ────────────────────────────────────────────────────

@app.get("/auth/zerodha/login-url")
async def zerodha_login_url():
    """Get Zerodha OAuth login URL."""
    from app.core.auth.zerodha_auth import generate_login_url
    return {"url": generate_login_url()}


@app.post("/auth/zerodha/callback")
async def zerodha_callback(body: dict):
    """Exchange request_token for access_token."""
    from app.core.auth.zerodha_auth import generate_session
    request_token = body.get("request_token", "")
    if not request_token:
        raise HTTPException(status_code=400, detail="request_token required")
    result = generate_session(request_token)
    if not result:
        raise HTTPException(status_code=400, detail="Session generation failed")
    return {"status": "connected", **result}


@app.get("/auth/zerodha/status")
async def zerodha_status():
    """Check Zerodha connection status."""
    from app.core.auth.zerodha_auth import is_token_valid
    return {
        "data_source": getattr(app.state, "data_source", "mock"),
        "connected": is_token_valid(),
        "token_valid": is_token_valid(),
    }


# ─── Report Endpoint ───────────────────────────────────────────────────────────

@app.get("/report/summary")
async def get_report_summary():
    """Generate a comprehensive session report."""
    trades = portfolio_manager.get_trades()
    analytics = compute_analytics(trades, settings.initial_capital)
    positions = portfolio_manager.get_positions()
    all_events = event_bus.get_recent_events(200)

    # Top/bottom trades
    sell_trades = [t for t in trades if t["direction"] == "SELL" and t.get("pnl", 0) != 0]
    sorted_by_pnl = sorted(sell_trades, key=lambda t: t.get("pnl", 0), reverse=True)
    top_trades = sorted_by_pnl[:3]
    bottom_trades = sorted_by_pnl[-3:] if len(sorted_by_pnl) >= 3 else sorted_by_pnl

    # Strategy signal counts
    signal_events = [e for e in all_events if e["event"] == "SIGNAL_GENERATED"]
    strategy_signals: dict[str, int] = {}
    for e in signal_events:
        for sname in ["ema_cross", "rsi_mean_reversion", "bollinger_bands"]:
            if sname in e.get("detail", ""):
                strategy_signals[sname] = strategy_signals.get(sname, 0) + 1

    tick_stats = event_bus.get_tick_stats()

    return {
        "generated_at": datetime.now().isoformat(),
        "session_start": getattr(app.state, "session_start", ""),
        "data_source": getattr(app.state, "data_source", "mock"),
        "portfolio": portfolio_manager.get_portfolio_summary(),
        "positions": positions,
        "analytics": analytics,
        "strategies": [
            {
                "name": n,
                "active": strategy_registry.get(n).is_active,
                "config": _get_strategy_config(n),
                "signals_generated": strategy_signals.get(n, 0),
            }
            for n in strategy_registry.list_all()
        ],
        "risk_summary": {
            "total_rejections": sum(1 for e in all_events if e["event"] == "ORDER_REJECTED"),
        },
        "session": {
            "total_ticks": tick_stats["total_ticks"],
            "total_events": tick_stats["total_events"],
        },
        "top_trades": top_trades,
        "bottom_trades": bottom_trades,
        "total_trades": len(trades),
    }


# ─── Logs Endpoint ─────────────────────────────────────────────────────────────

@app.get("/logs/recent")
async def get_logs():
    """Return the last 100 lines from the log file."""
    return get_recent_logs(100)
