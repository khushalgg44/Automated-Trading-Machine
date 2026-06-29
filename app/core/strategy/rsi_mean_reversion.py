"""RSI Mean Reversion strategy — buys oversold, sells overbought.

RSI(14) below 30 → BUY (oversold, expect reversion up)
RSI(14) above 70 → SELL (overbought, expect reversion down)
"""

from typing import Any

from app.config import settings
from app.event_bus import event_bus, Events
from app.core.strategy.base_strategy import BaseStrategy, Signal
from app.core.market.watchlist import watchlist


class RSIMeanReversionStrategy(BaseStrategy):
    name = "rsi_mean_reversion"

    def __init__(
        self,
        period: int = settings.rsi_period,
        oversold: int = settings.rsi_oversold,
        overbought: int = settings.rsi_overbought,
        qty: int = 10,
    ) -> None:
        super().__init__()
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.qty = qty

        # Per-symbol price history for RSI calculation
        self._prices: dict[str, list[float]] = {}
        # Track last signal direction to avoid repeated signals
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

        # Need at least period+1 prices to compute RSI
        if len(self._prices[symbol]) < self.period + 1:
            return None

        # Keep only what we need (sliding window)
        if len(self._prices[symbol]) > self.period + 1:
            self._prices[symbol] = self._prices[symbol][-(self.period + 1):]

        rsi = self._calculate_rsi(self._prices[symbol])
        if rsi is None:
            return None

        # Generate signals on threshold crossing
        if rsi < self.oversold and self._last_signal[symbol] != Signal.BUY:
            self._last_signal[symbol] = Signal.BUY
            return Signal(
                direction=Signal.BUY,
                symbol=symbol,
                quantity=self.qty,
                reason=f"RSI({self.period})={rsi:.1f} < {self.oversold} (oversold)",
            )
        elif rsi > self.overbought and self._last_signal[symbol] != Signal.SELL:
            self._last_signal[symbol] = Signal.SELL
            return Signal(
                direction=Signal.SELL,
                symbol=symbol,
                quantity=self.qty,
                reason=f"RSI({self.period})={rsi:.1f} > {self.overbought} (overbought)",
            )
        elif self.oversold <= rsi <= self.overbought:
            # Reset signal state when RSI is in neutral zone
            self._last_signal[symbol] = None

        return None

    def _calculate_rsi(self, prices: list[float]) -> float | None:
        """Calculate RSI from a list of prices (needs period+1 values)."""
        if len(prices) < self.period + 1:
            return None

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))

        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi
