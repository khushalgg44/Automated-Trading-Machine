"""Smoke test: run mock generator for a simulated session,
assert at least one trade gets created.
"""

import asyncio
import sys
import os

# Ensure app module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# Remove any stale state file before test
STATE_FILE = "state.json"
if os.path.exists(STATE_FILE):
    os.remove(STATE_FILE)


@pytest.mark.asyncio
async def test_full_session_produces_trades():
    """Run tick generator through enough ticks to trigger EMA crossovers."""
    # Fresh imports so singletons initialize cleanly
    from app.config import settings
    from app.event_bus import event_bus, Events
    from app.core.market.price_cache import price_cache
    from app.core.market.mock_tick_generator import MockTickGenerator
    from app.core.strategy.ema_cross import EMACrossStrategy
    from app.core.risk.manager import risk_manager
    from app.core.trading.paper_engine import paper_engine
    from app.core.trading.portfolio_manager import portfolio_manager
    from app.core.strategy.base_strategy import Signal

    # Reset portfolio state for clean test
    portfolio_manager.capital = settings.initial_capital
    portfolio_manager.positions = {}
    portfolio_manager.trades = []

    # Create a fresh strategy instance for the test
    strategy = EMACrossStrategy(fast_period=3, slow_period=7, qty=5)

    # Wire up signal → order flow manually for isolation
    trades_captured: list[dict] = []

    async def on_signal(payload):
        signal: Signal = payload["signal"]
        approved, reason = risk_manager.check(signal)
        if approved:
            trade = await paper_engine.fill_order(signal)
            if trade:
                trades_captured.append(trade)

    event_bus.subscribe(Events.SIGNAL_GENERATED, on_signal)
    await strategy.start()

    # Create generator with faster ticks for test
    generator = MockTickGenerator()
    generator._prepare_candles()

    # Replay first 100 candles (enough for several crossovers)
    for i in range(100):
        for symbol in settings.symbols:
            candle = generator._candles[symbol][i]
            tick_payload = {
                "symbol": candle["symbol"],
                "ltp": candle["close"],
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle["volume"],
                "timestamp": candle["timestamp"],
            }
            await event_bus.publish(Events.TICK_RECEIVED, tick_payload)

    await strategy.stop()
    event_bus.unsubscribe(Events.SIGNAL_GENERATED, on_signal)

    # Assert at least one trade was created
    assert len(trades_captured) > 0, "Expected at least one trade from EMA crossovers"
    print(f"\n✅ Smoke test passed: {len(trades_captured)} trades executed")
    for t in trades_captured[:5]:
        print(f"   {t['direction']} {t['qty']}x {t['symbol']} @ ₹{t['price']:.2f}")

    # Cleanup
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
