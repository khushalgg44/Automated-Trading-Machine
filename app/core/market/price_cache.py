"""In-memory latest-price cache, updated on every tick."""

from typing import Any

from app.event_bus import event_bus, Events


class PriceCache:
    """Stores the latest price for each symbol.

    Subscribes to TICK_RECEIVED events automatically.
    Also maintains a rolling history of last 100 prices per symbol for correlation analysis.
    """

    def __init__(self) -> None:
        self._prices: dict[str, float] = {}
        self._price_history: dict[str, list[float]] = {}
        event_bus.subscribe(Events.TICK_RECEIVED, self._on_tick)

    async def _on_tick(self, payload: dict[str, Any]) -> None:
        symbol = payload["symbol"]
        price = payload["ltp"]  # last traded price
        self._prices[symbol] = price

        # Maintain rolling history of last 100 prices per symbol
        if symbol not in self._price_history:
            self._price_history[symbol] = []
        self._price_history[symbol].append(price)
        if len(self._price_history[symbol]) > 100:
            self._price_history[symbol] = self._price_history[symbol][-100:]

    def get(self, symbol: str) -> float | None:
        return self._prices.get(symbol)

    def get_all(self) -> dict[str, float]:
        return dict(self._prices)

    def get_history(self, symbol: str, count: int = 50) -> list[float]:
        """Get the last `count` prices for a symbol."""
        history = self._price_history.get(symbol, [])
        return history[-count:]

    def get_all_history(self, count: int = 50) -> dict[str, list[float]]:
        """Get the last `count` prices for all symbols."""
        return {sym: hist[-count:] for sym, hist in self._price_history.items()}


# Singleton
price_cache = PriceCache()
