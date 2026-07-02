"""EMA Crossover strategy — generates BUY/SELL signals on fast/slow EMA cross.

Uses short periods (fast=3, slow=7) to produce frequent crossovers for demo.
"""

from typing import Any

from app.config import settings
from app.event_bus import event_bus, Events
from app.core.strategy.base_strategy import BaseStrategy, Signal
from app.core.market.watchlist import watchlist


def _ema(prev_ema: float, price: float, period: int) -> float:
    """Calculate the next EMA value given previous EMA and new price."""
    k = 2.0 / (period + 1)
    return price * k + prev_ema * (1 - k)


class EMACrossStrategy(BaseStrategy):
    name = "ema_cross"

    def __init__(
        self,
        fast_period: int = settings.ema_fast_period,
        slow_period: int = settings.ema_slow_period,
        qty: int = 5,
    ) -> None:
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.qty = qty

        # Per-symbol EMA state
        self._fast_ema: dict[str, float] = {}
        self._slow_ema: dict[str, float] = {}
        self._prev_fast_above: dict[str, bool | None] = {}
        self._tick_count: dict[str, int] = {}
        # Track positions for stop-loss
        self._entry_price: dict[str, float] = {}
        self._stop_loss_pct: float = 0.005  # 0.5% stop-loss

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

        # Initialize on first tick
        if symbol not in self._fast_ema:
            self._fast_ema[symbol] = price
            self._slow_ema[symbol] = price
            self._prev_fast_above[symbol] = None
            self._tick_count[symbol] = 0
            return None

        self._tick_count[symbol] += 1

        # Stop-loss check: if we have a position and it's losing > threshold, exit
        if symbol in self._entry_price:
            entry = self._entry_price[symbol]
            loss_pct = (entry - price) / entry
            if loss_pct >= self._stop_loss_pct:
                del self._entry_price[symbol]
                return Signal(
                    direction=Signal.SELL,
                    symbol=symbol,
                    quantity=self.qty,
                    reason=f"Stop-loss triggered ({loss_pct*100:.2f}% loss)",
                )

        # Update EMAs
        self._fast_ema[symbol] = _ema(self._fast_ema[symbol], price, self.fast_period)
        self._slow_ema[symbol] = _ema(self._slow_ema[symbol], price, self.slow_period)

        fast_above = self._fast_ema[symbol] > self._slow_ema[symbol]
        prev = self._prev_fast_above[symbol]
        self._prev_fast_above[symbol] = fast_above

        # Need at least slow_period ticks before generating signals
        if self._tick_count[symbol] < self.slow_period:
            return None

        if prev is None:
            return None

        # Crossover detection
        if fast_above and not prev:
            self._entry_price[symbol] = price  # Track entry for stop-loss
            return Signal(
                direction=Signal.BUY,
                symbol=symbol,
                quantity=self.qty,
                reason=f"EMA{self.fast_period} crossed above EMA{self.slow_period}",
            )
        elif not fast_above and prev:
            if symbol in self._entry_price:
                del self._entry_price[symbol]
            return Signal(
                direction=Signal.SELL,
                symbol=symbol,
                quantity=self.qty,
                reason=f"EMA{self.fast_period} crossed below EMA{self.slow_period}",
            )

        return None
