"""Order log — stores all orders (filled + rejected) for the order tape.

Subscribes to ORDER_FILLED and ORDER_REJECTED events.
"""

from collections import deque
from datetime import datetime
from typing import Any

from app.event_bus import event_bus, Events


_MAX_ORDERS = 100


class OrderLog:
    """Maintains a log of all orders for the tape display."""

    def __init__(self) -> None:
        self._orders: deque[dict[str, Any]] = deque(maxlen=_MAX_ORDERS)
        self._id_counter = 0
        event_bus.subscribe(Events.ORDER_FILLED, self._on_filled)

    async def _on_filled(self, payload: dict[str, Any]) -> None:
        self._id_counter += 1
        self._orders.append({
            "id": self._id_counter,
            "timestamp": payload.get("timestamp", datetime.now().isoformat()),
            "symbol": payload.get("symbol", ""),
            "side": payload.get("direction", ""),
            "quantity": payload.get("qty", 0),
            "price": payload.get("price", 0),
            "status": "FILLED",
            "strategy": payload.get("strategy", ""),
            "rejection_reason": None,
        })

    def log_rejection(self, symbol: str, side: str, quantity: int, price: float, strategy: str, reason: str) -> None:
        """Manually log a rejected order."""
        self._id_counter += 1
        self._orders.append({
            "id": self._id_counter,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "status": "REJECTED",
            "strategy": strategy,
            "rejection_reason": reason,
        })

    def get_orders(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent orders in reverse chronological order."""
        items = list(self._orders)
        return items[-limit:]


# Singleton
order_log = OrderLog()
