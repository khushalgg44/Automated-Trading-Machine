"""Tests for backtest engine — isolation and correctness."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch

from app.core.backtest.engine import run_backtest
from app.core.trading.portfolio_manager import portfolio_manager
from app.config import settings


@pytest.mark.asyncio
async def test_backtest_isolated_from_live_portfolio():
    """Running a backtest should NOT modify the live portfolio."""
    # Record live state before backtest
    live_capital_before = portfolio_manager.capital
    live_trades_before = len(portfolio_manager.trades)

    # Simple candles that will trigger EMA crossover
    candles = [
        {"date": f"2025-01-{i+1:02d}", "open": p, "high": p+2, "low": p-2, "close": p, "volume": 10000}
        for i, p in enumerate([100, 99, 98, 97, 96, 95, 96, 98, 101, 104, 108, 112, 115, 118, 120])
    ]

    result = await run_backtest(
        strategy_name="ema_cross",
        symbol="TEST",
        candles=candles,
        initial_capital=100000.0,
    )

    # Live portfolio must be unchanged
    assert portfolio_manager.capital == live_capital_before
    assert len(portfolio_manager.trades) == live_trades_before

    # Backtest should have run successfully
    assert result["candles_processed"] == 15
    assert result["strategy"] == "ema_cross"


@pytest.mark.asyncio
async def test_backtest_produces_trades_on_crossover():
    """With enough candles, EMA cross should generate at least one trade."""
    # Rising then falling prices to create crossovers
    prices = [100, 99, 98, 97, 96, 95, 94, 95, 97, 100, 103, 107, 110, 108, 105, 102, 99, 96, 93, 91]
    candles = [
        {"date": f"2025-01-{i+1:02d}", "open": p, "high": p+1, "low": p-1, "close": p, "volume": 10000}
        for i, p in enumerate(prices)
    ]

    result = await run_backtest(
        strategy_name="ema_cross",
        symbol="TEST",
        candles=candles,
        initial_capital=100000.0,
    )

    assert result["total_trades"] > 0, "Expected at least one trade from EMA crossovers"
    assert len(result["equity_curve"]) == len(candles)


@pytest.mark.asyncio
async def test_backtest_rsi_strategy():
    """RSI strategy should generate signals on extreme prices."""
    # Heavily declining prices to trigger RSI oversold
    prices = [100, 98, 95, 92, 88, 84, 80, 76, 72, 68, 64, 60, 56, 52, 48, 45, 43, 42, 50, 55]
    candles = [
        {"date": f"2025-01-{i+1:02d}", "open": p, "high": p+1, "low": p-1, "close": p, "volume": 10000}
        for i, p in enumerate(prices)
    ]

    result = await run_backtest(
        strategy_name="rsi_mean_reversion",
        symbol="TEST",
        candles=candles,
        initial_capital=100000.0,
    )

    assert result["candles_processed"] == 20
    assert result["strategy"] == "rsi_mean_reversion"
    # With 14 period RSI and steep decline, should get at least 1 signal
    assert result["total_trades"] >= 1


@pytest.mark.asyncio
async def test_backtest_returns_equity_curve():
    """Equity curve should have one point per candle."""
    candles = [
        {"date": f"2025-01-{i+1:02d}", "open": 100+i, "high": 102+i, "low": 99+i, "close": 100+i, "volume": 10000}
        for i in range(30)
    ]

    result = await run_backtest(
        strategy_name="bollinger_bands",
        symbol="TEST",
        candles=candles,
        initial_capital=100000.0,
    )

    assert len(result["equity_curve"]) == 30
    # First point should be near initial capital
    assert abs(result["equity_curve"][0]["equity"] - 100000.0) < 1000
