"""Tests for trading strategies — verify signal generation logic."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.core.strategy.ema_cross import EMACrossStrategy
from app.core.strategy.rsi_mean_reversion import RSIMeanReversionStrategy
from app.core.strategy.bollinger_bands import BollingerBandsStrategy
from app.core.strategy.base_strategy import Signal


@pytest.mark.asyncio
async def test_ema_cross_buy_signal():
    """EMA fast crossing above slow should generate BUY."""
    strategy = EMACrossStrategy(fast_period=3, slow_period=5, qty=10)
    strategy._active = True

    # Feed declining prices (slow EMA stays above fast)
    declining = [100, 99, 98, 97, 96, 95, 94]
    for p in declining:
        await strategy.on_tick({"symbol": "TEST", "ltp": p})

    # Now feed rising prices to cause fast EMA to cross above slow
    rising = [95, 97, 100, 103, 106, 110, 115]
    signals = []
    for p in rising:
        sig = await strategy.on_tick({"symbol": "TEST", "ltp": p})
        if sig:
            signals.append(sig)

    buy_signals = [s for s in signals if s.direction == Signal.BUY]
    assert len(buy_signals) >= 1, "Expected at least one BUY signal on upward crossover"


@pytest.mark.asyncio
async def test_ema_cross_sell_signal():
    """EMA fast crossing below slow should generate SELL."""
    strategy = EMACrossStrategy(fast_period=3, slow_period=5, qty=10)
    strategy._active = True

    # Feed rising prices first
    rising = [100, 101, 102, 103, 104, 105, 106, 107, 108]
    for p in rising:
        await strategy.on_tick({"symbol": "TEST", "ltp": p})

    # Now feed declining prices to cause crossover down
    declining = [107, 105, 102, 99, 96, 93, 90]
    signals = []
    for p in declining:
        sig = await strategy.on_tick({"symbol": "TEST", "ltp": p})
        if sig:
            signals.append(sig)

    sell_signals = [s for s in signals if s.direction == Signal.SELL]
    assert len(sell_signals) >= 1, "Expected at least one SELL signal on downward crossover"


@pytest.mark.asyncio
async def test_ema_cross_no_signal_during_warmup():
    """No signals until slow_period ticks have been received."""
    strategy = EMACrossStrategy(fast_period=3, slow_period=7, qty=10)
    strategy._active = True

    # Feed exactly 6 ticks (less than slow_period=7)
    signals = []
    for p in [100, 105, 110, 115, 120, 125]:
        sig = await strategy.on_tick({"symbol": "TEST", "ltp": p})
        if sig:
            signals.append(sig)

    assert len(signals) == 0, "Should not generate signals during warmup"


@pytest.mark.asyncio
async def test_rsi_buy_signal_oversold():
    """RSI below oversold threshold should generate BUY."""
    strategy = RSIMeanReversionStrategy(period=5, oversold=30, overbought=70, qty=10)
    strategy._active = True

    # Feed consistently declining prices to drive RSI below 30
    prices = [100, 99, 97, 95, 92, 89, 86, 83, 80, 77]
    signals = []
    for p in prices:
        sig = await strategy.on_tick({"symbol": "TEST", "ltp": p})
        if sig:
            signals.append(sig)

    buy_signals = [s for s in signals if s.direction == Signal.BUY]
    assert len(buy_signals) >= 1, "Expected BUY signal when RSI drops below 30"


@pytest.mark.asyncio
async def test_rsi_sell_signal_overbought():
    """RSI above overbought threshold should generate SELL."""
    strategy = RSIMeanReversionStrategy(period=5, oversold=30, overbought=70, qty=10)
    strategy._active = True

    # Feed consistently rising prices to drive RSI above 70
    prices = [100, 102, 105, 108, 112, 116, 121, 127, 134, 142]
    signals = []
    for p in prices:
        sig = await strategy.on_tick({"symbol": "TEST", "ltp": p})
        if sig:
            signals.append(sig)

    sell_signals = [s for s in signals if s.direction == Signal.SELL]
    assert len(sell_signals) >= 1, "Expected SELL signal when RSI rises above 70"


@pytest.mark.asyncio
async def test_rsi_no_signal_during_warmup():
    """No signals until period+1 prices received."""
    strategy = RSIMeanReversionStrategy(period=14, oversold=30, overbought=70, qty=10)
    strategy._active = True

    # Feed only 10 prices (less than period+1=15)
    signals = []
    for p in [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]:
        sig = await strategy.on_tick({"symbol": "TEST", "ltp": p})
        if sig:
            signals.append(sig)

    assert len(signals) == 0, "Should not generate signals before warmup completes"


@pytest.mark.asyncio
async def test_bollinger_buy_below_lower_band():
    """Price below lower band should generate BUY."""
    # Use period=10 so that we have 10 stable prices establishing tight bands,
    # then the extreme price on tick 11 is compared against bands computed from ticks 2-11
    strategy = BollingerBandsStrategy(period=10, std_dev_multiplier=2.0, qty=10)
    strategy._active = True

    # Feed 12 stable prices to establish bands (needs at least period to start)
    stable = [100.0, 100.0, 100.1, 99.9, 100.0, 100.1, 99.9, 100.0, 100.0, 100.1, 99.9, 100.0]
    for p in stable:
        await strategy.on_tick({"symbol": "TEST", "ltp": p})

    # Now a price far below the lower band (bands are ~99.7 to 100.3 with std~0.08)
    signals = []
    sig = await strategy.on_tick({"symbol": "TEST", "ltp": 95.0})
    if sig:
        signals.append(sig)

    buy_signals = [s for s in signals if s.direction == Signal.BUY]
    assert len(buy_signals) >= 1, "Expected BUY when price drops well below lower band"


@pytest.mark.asyncio
async def test_bollinger_sell_above_upper_band():
    """Price above upper band should generate SELL."""
    strategy = BollingerBandsStrategy(period=10, std_dev_multiplier=2.0, qty=10)
    strategy._active = True

    # Feed 12 stable prices
    stable = [100.0, 100.0, 100.1, 99.9, 100.0, 100.1, 99.9, 100.0, 100.0, 100.1, 99.9, 100.0]
    for p in stable:
        await strategy.on_tick({"symbol": "TEST", "ltp": p})

    # Price far above upper band
    signals = []
    sig = await strategy.on_tick({"symbol": "TEST", "ltp": 105.0})
    if sig:
        signals.append(sig)

    sell_signals = [s for s in signals if s.direction == Signal.SELL]
    assert len(sell_signals) >= 1, "Expected SELL when price rises well above upper band"


@pytest.mark.asyncio
async def test_bollinger_no_signal_during_warmup():
    """No signals until period candles accumulated."""
    strategy = BollingerBandsStrategy(period=20, std_dev_multiplier=2.0, qty=10)
    strategy._active = True

    # Feed only 15 prices (less than period=20)
    signals = []
    for p in range(100, 115):
        sig = await strategy.on_tick({"symbol": "TEST", "ltp": float(p)})
        if sig:
            signals.append(sig)

    assert len(signals) == 0, "Should not signal during warmup"
