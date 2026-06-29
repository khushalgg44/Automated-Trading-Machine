"""Real-time candle aggregator — aggregates ticks into OHLC candles.

Supports 1-minute and 5-minute timeframes.
Maintains rolling buffers of completed candles per symbol.
"""

import math
from collections import deque
from datetime import datetime
from typing import Any

from app.event_bus import event_bus, Events


_MAX_CANDLES = 60


class CandleAggregator:
    """Aggregates raw ticks into 1m and 5m OHLC candles."""

    def __init__(self) -> None:
        # 1-minute candles
        self._completed_1m: dict[str, deque] = {}
        self._current_1m: dict[str, dict[str, Any]] = {}
        self._current_minute: dict[str, str] = {}
        # 5-minute candles
        self._completed_5m: dict[str, deque] = {}
        self._pending_5m: dict[str, list] = {}  # accumulates 1m candles for 5m aggregation
        # Subscribe
        event_bus.subscribe(Events.TICK_RECEIVED, self._on_tick)

    async def _on_tick(self, payload: dict[str, Any]) -> None:
        symbol = payload["symbol"]
        price = payload["ltp"]
        volume = payload.get("volume", 0)
        now = datetime.now()
        minute_key = now.strftime("%Y-%m-%d %H:%M")

        if symbol not in self._completed_1m:
            self._completed_1m[symbol] = deque(maxlen=_MAX_CANDLES)
            self._completed_5m[symbol] = deque(maxlen=_MAX_CANDLES)
            self._pending_5m[symbol] = []
            self._current_minute[symbol] = minute_key
            self._current_1m[symbol] = {
                "timestamp": now.isoformat(),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
            return

        if minute_key != self._current_minute[symbol]:
            # Close 1m candle
            completed_candle = self._current_1m[symbol]
            self._completed_1m[symbol].append(completed_candle)

            # Aggregate into 5m
            self._pending_5m[symbol].append(completed_candle)
            if len(self._pending_5m[symbol]) >= 5:
                batch = self._pending_5m[symbol][:5]
                self._pending_5m[symbol] = self._pending_5m[symbol][5:]
                candle_5m = {
                    "timestamp": batch[0]["timestamp"],
                    "open": batch[0]["open"],
                    "high": max(c["high"] for c in batch),
                    "low": min(c["low"] for c in batch),
                    "close": batch[-1]["close"],
                    "volume": sum(c["volume"] for c in batch),
                }
                self._completed_5m[symbol].append(candle_5m)

            # Start new 1m candle
            self._current_minute[symbol] = minute_key
            self._current_1m[symbol] = {
                "timestamp": now.isoformat(),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
        else:
            candle = self._current_1m[symbol]
            candle["high"] = max(candle["high"], price)
            candle["low"] = min(candle["low"], price)
            candle["close"] = price
            candle["volume"] += volume

    def get_candles(self, symbol: str, timeframe: str = "1m") -> list[dict[str, Any]]:
        """Return completed candles + current in-progress candle."""
        if timeframe == "5m":
            completed = list(self._completed_5m.get(symbol, []))
            return completed

        completed = list(self._completed_1m.get(symbol, []))
        current = self._current_1m.get(symbol)
        if current:
            completed.append({**current, "in_progress": True})
        return completed

    def get_indicators(self, symbol: str, timeframe: str = "1m") -> dict[str, Any]:
        """Compute EMA and Bollinger Band indicators from candle close prices."""
        candles = self.get_candles(symbol, timeframe)
        closes = [c["close"] for c in candles]

        result: dict[str, Any] = {"ema_fast": [], "ema_slow": [], "bb_upper": [], "bb_middle": [], "bb_lower": []}

        if len(closes) < 2:
            return result

        # EMA computation (fast=3, slow=7)
        fast_period = 3
        slow_period = 7
        ema_fast = _compute_ema(closes, fast_period)
        ema_slow = _compute_ema(closes, slow_period)
        result["ema_fast"] = ema_fast
        result["ema_slow"] = ema_slow

        # Bollinger Bands (period=20, std=2)
        bb_period = 20
        bb_std = 2.0
        bb_upper, bb_middle, bb_lower = _compute_bollinger(closes, bb_period, bb_std)
        result["bb_upper"] = bb_upper
        result["bb_middle"] = bb_middle
        result["bb_lower"] = bb_lower

        return result


def _compute_ema(prices: list[float], period: int) -> list[float | None]:
    """Compute EMA returning None for insufficient data points."""
    result: list[float | None] = []
    if len(prices) < period:
        return [None] * len(prices)

    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period

    for i in range(len(prices)):
        if i < period - 1:
            result.append(None)
        elif i == period - 1:
            result.append(round(ema, 2))
        else:
            ema = prices[i] * k + ema * (1 - k)
            result.append(round(ema, 2))

    return result


def _compute_bollinger(prices: list[float], period: int, std_mult: float) -> tuple[list, list, list]:
    """Compute Bollinger Bands returning None for insufficient data."""
    upper: list[float | None] = []
    middle: list[float | None] = []
    lower: list[float | None] = []

    for i in range(len(prices)):
        if i < period - 1:
            upper.append(None)
            middle.append(None)
            lower.append(None)
        else:
            window = prices[i - period + 1: i + 1]
            sma = sum(window) / period
            variance = sum((p - sma) ** 2 for p in window) / period
            std = math.sqrt(variance)
            middle.append(round(sma, 2))
            upper.append(round(sma + std_mult * std, 2))
            lower.append(round(sma - std_mult * std, 2))

    return upper, middle, lower


# Singleton
candle_aggregator = CandleAggregator()
