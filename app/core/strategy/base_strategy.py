"""Base strategy interface — all strategies inherit from this."""

from abc import ABC, abstractmethod
from typing import Any


class Signal:
    """A trading signal emitted by a strategy."""

    BUY = "BUY"
    SELL = "SELL"

    def __init__(self, direction: str, symbol: str, quantity: int, reason: str = ""):
        self.direction = direction
        self.symbol = symbol
        self.quantity = quantity
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "reason": self.reason,
        }


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    name: str = "base"

    def __init__(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    async def start(self) -> None:
        """Subscribe to events and begin processing."""
        self._active = True
        await self._on_start()

    async def stop(self) -> None:
        """Unsubscribe from events and stop processing."""
        self._active = False
        await self._on_stop()

    @abstractmethod
    async def _on_start(self) -> None:
        ...

    @abstractmethod
    async def _on_stop(self) -> None:
        ...

    @abstractmethod
    async def on_tick(self, payload: dict[str, Any]) -> Signal | None:
        """Process a tick and optionally return a signal."""
        ...
