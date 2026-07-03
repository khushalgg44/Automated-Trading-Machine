"""Custom strategy — dynamically created from user-defined rules via the Strategy Builder.

Each rule is: IF indicator comparator value THEN action
Rules are OR'd — any rule matching triggers the signal.
"""

import math
from typing import Any

from app.event_bus import event_bus, Events
from app.core.strategy.base_strategy import BaseStrategy, Signal
from app.core.market.watchlist import watchlist


class CustomStrategy(BaseStrategy):
    """A user-defined strategy built from visual rules."""

    def __init__(self, name: str, rules: list[dict[str, Any]], qty: int = 5) -> None:
        super().__init__()
        self.name = name
        self.rules = rules
        self.qty = qty

        # Per-symbol state
        self._prices: dict[str, list[float]] = {}
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
        if len(self._prices[symbol]) > 100:
            self._prices[symbol] = self._prices[symbol][-100:]

        # Need at least 21 prices for indicators
        if len(self._prices[symbol]) < 21:
            return None

        # Compute indicator values
        indicators = self._compute_indicators(self._prices[symbol])

        # Evaluate rules (OR logic)
        for rule in self.rules:
            result = self._evaluate_rule(rule, indicators, price)
            if result and result != self._last_signal[symbol]:
                self._last_signal[symbol] = result
                return Signal(
                    direction=result,
                    symbol=symbol,
                    quantity=self.qty,
                    reason=f"Custom rule: {rule['indicator']} {rule['comparator']} {rule['value']}",
                )

        return None

    def _compute_indicators(self, prices: list[float]) -> dict[str, float]:
        """Compute all indicator values from price history."""
        n = len(prices)

        # RSI (14 period)
        rsi = 50.0
        if n >= 15:
            gains = []
            losses = []
            for i in range(n - 14, n):
                diff = prices[i] - prices[i - 1]
                gains.append(max(0, diff))
                losses.append(max(0, -diff))
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            else:
                rsi = 100.0

        # EMA Fast (9)
        ema_fast = self._calc_ema(prices, 9)

        # EMA Slow (21)
        ema_slow = self._calc_ema(prices, 21)

        # Bollinger Bands (20, 2)
        bb_upper = 0.0
        bb_lower = 0.0
        if n >= 20:
            window = prices[-20:]
            sma = sum(window) / 20
            std = math.sqrt(sum((p - sma) ** 2 for p in window) / 20)
            bb_upper = sma + 2 * std
            bb_lower = sma - 2 * std

        return {
            "RSI": rsi,
            "EMA_FAST": ema_fast,
            "EMA_SLOW": ema_slow,
            "PRICE": prices[-1],
            "BOLLINGER_UPPER": bb_upper,
            "BOLLINGER_LOWER": bb_lower,
        }

    def _calc_ema(self, prices: list[float], period: int) -> float:
        if len(prices) < period:
            return prices[-1]
        k = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period
        for p in prices[period:]:
            ema = p * k + ema * (1 - k)
        return ema

    def _evaluate_rule(self, rule: dict[str, Any], indicators: dict[str, float], price: float) -> str | None:
        """Evaluate a single rule. Returns 'BUY', 'SELL', or None."""
        indicator_name = rule.get("indicator", "")
        comparator = rule.get("comparator", "")
        value_str = rule.get("value", "0")
        action = rule.get("action", "")

        # Get indicator value
        indicator_val = indicators.get(indicator_name, 0)

        # Get comparison value (could be a number or another indicator name)
        try:
            compare_val = float(value_str)
        except ValueError:
            compare_val = indicators.get(value_str, 0)

        # Evaluate comparison
        triggered = False
        if comparator == "above" and indicator_val > compare_val:
            triggered = True
        elif comparator == "below" and indicator_val < compare_val:
            triggered = True
        elif comparator == "crosses_above" and indicator_val > compare_val:
            triggered = True
        elif comparator == "crosses_below" and indicator_val < compare_val:
            triggered = True

        return action if triggered else None
