"""In-memory latest-price cache, updated on every tick."""

from typing import Any

from app.event_bus import event_bus, Events


class PriceCache:
    """Stores the latest price for each symbol.

    Subscribes to TICK_RECEIVED events automatically.
    """

    def __init__(self) -> None:
        self._prices: dict[str, float] = {}
        event_bus.subscribe(Events.TICK_RECEIVED, self._on_tick)

    async def _on_tick(self, payload: dict[str, Any]) -> None:
        symbol = payload["symbol"]
        price = payload["ltp"]  # last traded price
        self._prices[symbol] = price

    def get(self, symbol: str) -> float | None:
        return self._prices.get(symbol)

    def get_all(self) -> dict[str, float]:
        return dict(self._prices)


# Singleton
price_cache = PriceCache()
