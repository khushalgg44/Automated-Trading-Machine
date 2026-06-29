"""Bollinger Bands Mean Reversion strategy.

- Middle band: SMA(20)
- Upper band: SMA(20) + 2 × StdDev
- Lower band: SMA(20) - 2 × StdDev

Signals:
- Price crosses BELOW lower band → BUY (oversold)
- Price crosses ABOVE upper band → SELL (overbought)
"""

import math
from typing import Any

from app.config import settings
from app.event_bus import event_bus, Events
from app.core.strategy.base_strategy import BaseStrategy, Signal
from app.core.market.watchlist import watchlist


class BollingerBandsStrategy(BaseStrategy):
    name = "bollinger_bands"

    def __init__(
        self,
        period: int = 20,
        std_dev_multiplier: float = 2.0,
        qty: int = 10,
    ) -> None:
        super().__init__()
        self.period = period
        self.std_dev_multiplier = std_dev_multiplier
        self.qty = qty

        # Per-symbol price history
        self._prices: dict[str, list[float]] = {}
        # Track last signal to avoid repeated signals in same zone
        self._last_signal: dict[str, str | None] = {}

    async def _on_start(self) -> None:
        event_bus.subscribe(Events.TICK_RECEIVED, self._handle_tick)

    async def _on_stop(self) -> None:
        event_bus.unsubscribe(Events.TICK_RECEIVED, self._handle_tick)

    async def _handle_tick(self, payload: dict[str, Any]) -> None:
        if not watchlist.contains(payload["symbol"]):
            return
        signal = await self.on_tick(payload)
        if signal:
            await event_bus.publish(
                Events.SIGNAL_GENERATED,
                {"signal": signal, "strategy": self.name},
            )

    async def on_tick(self, payload: dict[str, Any]) -> Signal | None:
        if not self._active:
            return None

        symbol = payload["symbol"]
        price = payload["ltp"]

        # Accumulate prices
        if symbol not in self._prices:
            self._prices[symbol] = []
            self._last_signal[symbol] = None

        self._prices[symbol].append(price)

        # Need at least 'period' prices to compute bands
        if len(self._prices[symbol]) < self.period:
            return None

        # Keep sliding window
        if len(self._prices[symbol]) > self.period:
            self._prices[symbol] = self._prices[symbol][-self.period:]

        # Calculate SMA and standard deviation
        window = self._prices[symbol]
        sma = sum(window) / self.period
        variance = sum((p - sma) ** 2 for p in window) / self.period
        std_dev = math.sqrt(variance)

        upper_band = sma + self.std_dev_multiplier * std_dev
        lower_band = sma - self.std_dev_multiplier * std_dev

        # Signal generation
        if price < lower_band and self._last_signal[symbol] != Signal.BUY:
            self._last_signal[symbol] = Signal.BUY
            return Signal(
                direction=Signal.BUY,
                symbol=symbol,
                quantity=self.qty,
                reason=f"Price ₹{price:.2f} < Lower BB ₹{lower_band:.2f} (oversold)",
            )
        elif price > upper_band and self._last_signal[symbol] != Signal.SELL:
            self._last_signal[symbol] = Signal.SELL
            return Signal(
                direction=Signal.SELL,
                symbol=symbol,
                quantity=self.qty,
                reason=f"Price ₹{price:.2f} > Upper BB ₹{upper_band:.2f} (overbought)",
            )
        elif lower_band <= price <= upper_band:
            # Reset when price returns to normal range
            self._last_signal[symbol] = None

        return None
