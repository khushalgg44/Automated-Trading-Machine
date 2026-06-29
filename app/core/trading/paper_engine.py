"""Paper trading engine — fills orders at current market price (from PriceCache).

No real orders are ever placed. This simulates instant fills against
the latest price in the cache.
"""

from typing import Any

from app.core.market.price_cache import price_cache
from app.core.trading.portfolio_manager import portfolio_manager
from app.event_bus import event_bus, Events
from app.core.strategy.base_strategy import Signal


class PaperEngine:
    """Executes paper trades by filling at last known price."""

    async def fill_order(self, signal: Signal, strategy: str = "") -> dict[str, Any] | None:
        price = price_cache.get(signal.symbol)
        if price is None:
            return None

        if signal.direction == Signal.BUY:
            trade = portfolio_manager.execute_buy(
                signal.symbol, signal.quantity, price, strategy=strategy
            )
        elif signal.direction == Signal.SELL:
            trade = portfolio_manager.execute_sell(
                signal.symbol, signal.quantity, price, strategy=strategy
            )
        else:
            return None

        # Publish fill event
        await event_bus.publish(Events.ORDER_FILLED, trade)
        return trade


# Singleton
paper_engine = PaperEngine()
