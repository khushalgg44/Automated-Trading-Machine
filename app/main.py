"""FastAPI application — AlgoTradeX paper trading platform."""

import csv
import io
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
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
    app.state.kite_connector = None

    # Choose data source
    if settings.data_source == "zerodha":
        from app.core.auth.zerodha_auth import load_token, is_token_valid
        token = load_token()
        if token and is_token_valid():
            from app.core.market.kite_connector import KiteTickerConnector
            app.state.kite_connector = KiteTickerConnector(
                settings.zerodha_api_key, token
            )
            await app.state.kite_connector.start()
            if app.state.kite_connector.is_running:
                logger.info("Zerodha Kite WebSocket started.")
            else:
                logger.warning("Kite connector failed to start. Falling back to mock.")
                app.state.data_source = "mock"
                await mock_tick_generator.start()
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
    logger.info(f"Data source: {app.state.data_source}. Strategies active.")

    # Start Telegram bot
    from app.core.notifications.telegram import start_telegram_bot
    start_telegram_bot()

    yield
    # Shutdown
    await strategy_registry.stop_all()
    if app.state.kite_connector:
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


@app.get("/auth/zerodha/callback")
async def zerodha_callback(request_token: str, action: str = "login"):
    """Zerodha redirects here after user login. Exchange token and redirect to dashboard."""
    from app.core.auth.zerodha_auth import generate_login_url

    if not request_token:
        return HTMLResponse("<h2>Error: No request_token received</h2>", status_code=400)

    # Generate session directly using raw requests (bypass kiteconnect SSL issues)
    try:
        import hashlib
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Compute checksum: SHA256(api_key + request_token + api_secret)
        checksum = hashlib.sha256(
            (settings.zerodha_api_key + request_token + settings.zerodha_api_secret).encode()
        ).hexdigest()

        # Call Kite API directly
        resp = requests.post(
            "https://api.kite.trade/session/token",
            data={
                "api_key": settings.zerodha_api_key,
                "request_token": request_token,
                "checksum": checksum,
            },
            verify=False,
        )

        resp_data = resp.json()
        if resp_data.get("status") == "error":
            raise Exception(resp_data.get("message", "Unknown error"))

        data = resp_data["data"]
        access_token = data["access_token"]
    except Exception as e:
        error_msg = str(e)
        return HTMLResponse(
            f'<html><body style="font-family:system-ui;padding:40px;background:#111827;color:#f87171;">'
            f'<h2>Session generation failed</h2><pre>{error_msg}</pre>'
            f'<p style="color:#9ca3af;">API Key: {settings.zerodha_api_key}</p>'
            f'<p style="color:#9ca3af;">Request Token: {request_token[:10]}...</p>'
            f'<a href="{generate_login_url()}" style="color:#60a5fa;">Try again</a>'
            f'</body></html>',
            status_code=400,
        )

    # Store token
    from app.core.auth.zerodha_auth import _store_token
    _store_token(access_token)

    # Start Kite WebSocket connector with new token
    from app.core.market.kite_connector import KiteTickerConnector

    # Stop mock generator if running
    if mock_tick_generator.is_running:
        await mock_tick_generator.stop()

    # Start live connector
    app.state.kite_connector = KiteTickerConnector(settings.zerodha_api_key, access_token)
    await app.state.kite_connector.start()
    app.state.data_source = "zerodha"
    event_bus.log_custom("ZERODHA_CONNECTED", f"Logged in as {data.get('user_name', '')}")

    # Return HTML that redirects to dashboard
    return HTMLResponse("""
    <html>
    <head><title>AlgoTradeX — Login Successful</title></head>
    <body style="font-family:system-ui;text-align:center;padding:60px;background:#111827;color:#f3f4f6;">
        <h2 style="color:#4ade80;">✓ Zerodha Login Successful!</h2>
        <p>Redirecting to dashboard...</p>
        <script>setTimeout(function(){ window.location.href = 'http://localhost:5173'; }, 2000);</script>
    </body>
    </html>
    """)


@app.post("/auth/zerodha/callback")
async def zerodha_callback_post(body: dict):
    """Exchange request_token for access_token (API call variant)."""
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
    kite_running = app.state.kite_connector.is_running if app.state.kite_connector else False
    return {
        "data_source": getattr(app.state, "data_source", "mock"),
        "configured_source": settings.data_source,
        "connected": kite_running,
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


# ─── Demo Mode Endpoints ───────────────────────────────────────────────────────

_DEMO_ACTIVE = False
_NORMAL_TICK_INTERVAL = settings.tick_interval_ms


@app.post("/demo/start")
async def start_demo():
    """Start demo mode — fast ticks, quick signals, clean slate."""
    global _DEMO_ACTIVE

    # Reset portfolio
    portfolio_manager.reset()
    event_bus.clear_log()

    # Speed up ticks (50ms = 20 ticks/sec with 8 stocks = 160 ticks/sec)
    settings.tick_interval_ms = 50

    # Reduce strategy warmup for fast signal generation
    ema = strategy_registry.get("ema_cross")
    if ema:
        ema.fast_period = 2
        ema.slow_period = 4

    rsi = strategy_registry.get("rsi_mean_reversion")
    if rsi:
        rsi.period = 5

    # Ensure strategies are running
    await strategy_registry.start("ema_cross")
    await strategy_registry.start("rsi_mean_reversion")

    _DEMO_ACTIVE = True
    event_bus.log_custom("DEMO_STARTED", "Demo mode active — 10x speed, quick signals")
    return {"status": "demo_started", "message": "Demo mode active — fast ticks, quick signals"}


@app.post("/demo/stop")
async def stop_demo():
    """Stop demo mode — return to normal speed and default parameters."""
    global _DEMO_ACTIVE

    # Restore normal tick speed
    settings.tick_interval_ms = _NORMAL_TICK_INTERVAL

    # Restore strategy defaults
    ema = strategy_registry.get("ema_cross")
    if ema:
        ema.fast_period = 3
        ema.slow_period = 7

    rsi = strategy_registry.get("rsi_mean_reversion")
    if rsi:
        rsi.period = 14

    _DEMO_ACTIVE = False
    event_bus.log_custom("DEMO_STOPPED", "Returned to normal speed")
    return {"status": "demo_stopped", "message": "Returned to normal speed"}


@app.get("/demo/status")
async def demo_status():
    """Check if demo mode is active."""
    return {"active": _DEMO_ACTIVE}


# ─── Correlation Matrix Endpoint ───────────────────────────────────────────────

@app.get("/correlation")
async def get_correlation():
    """Compute Pearson correlation matrix between watchlist symbols using price history."""
    import math

    symbols = watchlist.symbols
    history = price_cache.get_all_history(50)

    # Only include symbols that have at least 10 prices
    valid_symbols = [s for s in symbols if len(history.get(s, [])) >= 10]

    if len(valid_symbols) < 2:
        return {"symbols": valid_symbols, "matrix": [[1.0]] if valid_symbols else []}

    def pearson(x: list[float], y: list[float]) -> float:
        """Compute Pearson correlation coefficient."""
        n = min(len(x), len(y))
        if n < 2:
            return 0.0
        x = x[-n:]
        y = y[-n:]
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
        if den_x == 0 or den_y == 0:
            return 0.0
        return round(num / (den_x * den_y), 4)

    matrix = []
    for i, sym_i in enumerate(valid_symbols):
        row = []
        for j, sym_j in enumerate(valid_symbols):
            if i == j:
                row.append(1.0)
            else:
                corr = pearson(history[sym_i], history[sym_j])
                row.append(corr)
        matrix.append(row)

    return {"symbols": valid_symbols, "matrix": matrix}


# ─── Telegram Status Endpoint ──────────────────────────────────────────────────

@app.get("/telegram/status")
async def telegram_status():
    """Check Telegram bot configuration status."""
    import os
    enabled = os.getenv("ALGOTRADEX_TELEGRAM_ENABLED", "false").lower() == "true"
    token = os.getenv("ALGOTRADEX_TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("ALGOTRADEX_TELEGRAM_CHAT_ID", "")
    configured = bool(token and chat_id)

    if not token:
        message = "Set ALGOTRADEX_TELEGRAM_BOT_TOKEN in .env to enable"
    elif not chat_id:
        message = "Set ALGOTRADEX_TELEGRAM_CHAT_ID in .env to enable"
    elif not enabled:
        message = "Set ALGOTRADEX_TELEGRAM_ENABLED=true in .env to activate"
    else:
        message = "Telegram notifications active"

    return {"enabled": enabled, "configured": configured, "message": message}


# ─── Historical Data Endpoint ──────────────────────────────────────────────────

@app.get("/historical/{symbol}")
async def get_historical_data(symbol: str, from_date: str, to_date: str, interval: str = "day"):
    """Fetch historical OHLC data from Zerodha for any stock and time period.
    
    Args:
        symbol: NSE stock symbol (e.g., RELIANCE, TCS)
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        interval: Candle interval - minute, 5minute, 15minute, 30minute, 60minute, day
    """
    import requests as req
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    from app.core.auth.zerodha_auth import load_token

    token = load_token()
    if not token:
        raise HTTPException(status_code=401, detail="Zerodha token not available. Please login first.")

    valid_intervals = ["minute", "5minute", "15minute", "30minute", "60minute", "day"]
    if interval not in valid_intervals:
        raise HTTPException(status_code=400, detail=f"Invalid interval. Use: {valid_intervals}")

    # First, get instrument token for the symbol
    headers = {"Authorization": f"token {settings.zerodha_api_key}:{token}"}

    # Fetch instruments to find the token
    try:
        instruments_resp = req.get(
            "https://api.kite.trade/instruments/NSE",
            headers=headers,
            verify=False,
        )
        if instruments_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch instruments from Zerodha")

        import csv as csv_mod
        reader = csv_mod.DictReader(io.StringIO(instruments_resp.text))
        instrument_token = None
        for row in reader:
            if row["tradingsymbol"] == symbol.upper():
                instrument_token = row["instrument_token"]
                break

        if not instrument_token:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found on NSE")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Instrument lookup failed: {str(e)}")

    # Fetch historical data
    try:
        hist_url = f"https://api.kite.trade/instruments/historical/{instrument_token}/{interval}"
        params = {"from": from_date, "to": to_date}

        hist_resp = req.get(hist_url, headers=headers, params=params, verify=False)

        if hist_resp.status_code != 200:
            error_data = hist_resp.json() if hist_resp.headers.get("content-type", "").startswith("application/json") else {}
            raise HTTPException(
                status_code=hist_resp.status_code,
                detail=error_data.get("message", f"Zerodha API error: {hist_resp.status_code}")
            )

        data = hist_resp.json()
        candles_raw = data.get("data", {}).get("candles", [])

        # Transform to our format: [timestamp, open, high, low, close, volume]
        candles = []
        for c in candles_raw:
            candles.append({
                "timestamp": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            })

        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "from": from_date,
            "to": to_date,
            "count": len(candles),
            "candles": candles,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Historical data fetch failed: {str(e)}")


@app.get("/historical/search/{query}")
async def search_instruments(query: str):
    """Search NSE instruments by name/symbol."""
    import requests as req
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    from app.core.auth.zerodha_auth import load_token

    token = load_token()
    if not token:
        raise HTTPException(status_code=401, detail="Zerodha token not available")

    headers = {"Authorization": f"token {settings.zerodha_api_key}:{token}"}

    try:
        resp = req.get("https://api.kite.trade/instruments/NSE", headers=headers, verify=False)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch instruments")

        import csv as csv_mod
        reader = csv_mod.DictReader(io.StringIO(resp.text))
        results = []
        query_upper = query.upper()
        for row in reader:
            if query_upper in row["tradingsymbol"] or query_upper in row.get("name", "").upper():
                results.append({
                    "symbol": row["tradingsymbol"],
                    "name": row.get("name", ""),
                    "token": row["instrument_token"],
                })
                if len(results) >= 20:
                    break

        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Strategy Builder Endpoint ─────────────────────────────────────────────────

class StrategyBuilderRequest(BaseModel):
    name: str
    rules: list[dict]


@app.post("/strategy-builder/create")
async def create_custom_strategy(body: StrategyBuilderRequest):
    """Create and start a custom strategy from builder rules."""
    from app.core.strategy.custom_strategy import CustomStrategy

    name = body.name.strip().lower().replace(" ", "_")
    if not name:
        raise HTTPException(status_code=400, detail="Strategy name required")

    # Check if name already exists
    if strategy_registry.get(name):
        # Stop and replace
        await strategy_registry.stop(name)

    # Create and register
    strategy = CustomStrategy(name=name, rules=body.rules, qty=5)
    strategy_registry.register(strategy)
    await strategy_registry.start(name)

    event_bus.log_custom(Events.STRATEGY_STARTED, f"Custom strategy '{name}' created with {len(body.rules)} rules")
    return {"status": "created", "name": name, "rules_count": len(body.rules)}


# ─── RL Agent Endpoints ────────────────────────────────────────────────────────

class RLTrainRequest(BaseModel):
    symbol: str
    timesteps: int = 20000


@app.post("/rl/train")
async def train_rl(body: RLTrainRequest):
    """Train an RL agent on historical data for a symbol."""
    from app.core.strategy.rl_agent import train_rl_agent
    from app.core.backtest.data_loader import load_csv

    symbol = body.symbol.upper()

    # Try to get prices from historical data files
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    prices = []

    # Check for CSV files
    for filename in os.listdir(data_dir):
        if symbol.lower() in filename.lower() and filename.endswith(".csv"):
            candles = load_csv(os.path.join(data_dir, filename))
            prices = [c["close"] for c in candles]
            break

    if not prices or len(prices) < 50:
        raise HTTPException(status_code=400, detail=f"Not enough historical data for {symbol}. Need at least 50 candles.")

    try:
        result = train_rl_agent(prices, symbol, timesteps=body.timesteps)
        event_bus.log_custom("RL_TRAINED", f"RL agent trained for {symbol}: {result['final_return_pct']}% return, {result['trades']} trades")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@app.post("/rl/deploy/{symbol}")
async def deploy_rl(symbol: str):
    """Deploy a trained RL agent as a live strategy."""
    from app.core.strategy.rl_agent import RLAgentStrategy, load_rl_model

    symbol = symbol.upper()
    model = load_rl_model(symbol)
    if not model:
        raise HTTPException(status_code=404, detail=f"No trained model for {symbol}. Train first via POST /rl/train")

    # Register and start
    strategy = RLAgentStrategy(symbol=symbol, qty=5)
    strategy_registry.register(strategy)
    await strategy_registry.start("rl_agent")
    event_bus.log_custom(Events.STRATEGY_STARTED, f"RL Agent deployed for {symbol}")
    return {"status": "deployed", "symbol": symbol, "strategy": "rl_agent"}


@app.get("/rl/status")
async def rl_status():
    """Check if RL model exists and its status."""
    from app.core.strategy.rl_agent import _MODELS_DIR, get_training_progress
    models = []
    if os.path.exists(_MODELS_DIR):
        for f in os.listdir(_MODELS_DIR):
            if f.endswith(".zip"):
                models.append(f.replace("rl_", "").replace(".zip", "").upper())
    
    rl_strategy = strategy_registry.get("rl_agent")
    confidence = {}
    if rl_strategy and hasattr(rl_strategy, "get_confidence"):
        confidence = rl_strategy.get_confidence()

    progress = get_training_progress()

    return {
        "trained_models": models,
        "deployed": rl_strategy.is_active if rl_strategy else False,
        "confidence": confidence,
        "training_progress": progress,
    }
