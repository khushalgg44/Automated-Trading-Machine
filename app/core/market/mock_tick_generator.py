"""Mock tick generator — replays synthetic random-walk OHLC data as live ticks.

Publishes TICK_RECEIVED events through the event bus at a configurable speed.
Generates ticks for ALL stocks in the universe (8 stocks).
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any

from app.config import settings
from app.event_bus import event_bus, Events


# Base prices roughly matching real NSE levels
_BASE_PRICES: dict[str, float] = {
    "RELIANCE": 2500.0,
    "TCS": 3700.0,
    "INFY": 1550.0,
    "HDFCBANK": 1650.0,
    "SBIN": 820.0,
    "WIPRO": 450.0,
    "ICICIBANK": 1280.0,
    "BHARTIARTL": 1750.0,
}

# Volatility scaling: higher-priced stocks have slightly less % volatility
_VOLATILITY: dict[str, float] = {
    "RELIANCE": 0.0015,
    "TCS": 0.0012,
    "INFY": 0.0016,
    "HDFCBANK": 0.0014,
    "SBIN": 0.0020,
    "WIPRO": 0.0018,
    "ICICIBANK": 0.0015,
    "BHARTIARTL": 0.0013,
}


def _generate_synthetic_candles(
    symbol: str, base_price: float, num_candles: int = 375
) -> list[dict[str, Any]]:
    """Generate synthetic 1-min OHLC candles using a random walk.

    375 candles ≈ one full NSE session (9:15 AM to 3:30 PM).
    """
    candles = []
    price = base_price
    ts = datetime(2025, 1, 6, 9, 15)  # Monday market open
    vol = _VOLATILITY.get(symbol, 0.0015)

    for _ in range(num_candles):
        open_price = price
        changes = [random.gauss(0, vol) for _ in range(4)]
        prices = [open_price * (1 + c) for c in changes]
        high = max(open_price, *prices)
        low = min(open_price, *prices)
        close = prices[-1]
        volume = random.randint(5000, 50000)

        candles.append(
            {
                "symbol": symbol,
                "timestamp": ts.isoformat(),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume,
            }
        )
        price = close
        ts += timedelta(minutes=1)

    return candles


class MockTickGenerator:
    """Replays synthetic candle data as tick events for all universe stocks."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None
        self._candles: dict[str, list[dict[str, Any]]] = {}

    def _prepare_candles(self) -> None:
        """Generate candles for the entire universe."""
        for symbol in settings.universe:
            base = _BASE_PRICES.get(symbol, 1000.0)
            self._candles[symbol] = _generate_synthetic_candles(symbol, base)

    async def start(self) -> None:
        if self._running:
            return
        self._prepare_candles()
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def _run(self) -> None:
        """Iterate through candles and emit ticks. Loops indefinitely."""
        delay = settings.tick_interval_ms / 1000.0

        while self._running:
            num_candles = len(next(iter(self._candles.values())))

            for i in range(num_candles):
                if not self._running:
                    return

                for symbol in settings.universe:
                    candle = self._candles[symbol][i]
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

                await asyncio.sleep(delay)

            # Session complete — regenerate fresh candles and loop
            self._prepare_candles()


# Singleton
mock_tick_generator = MockTickGenerator()
