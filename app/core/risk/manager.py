"""Risk manager — validates signals before order execution.

Runs a chain of validators in sequence (short-circuit on first rejection).
Chain order: CapitalAvailable → MaxOpenPositions → MaxDailyLoss.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from app.config import settings
from app.core.market.price_cache import price_cache
from app.core.trading.portfolio_manager import portfolio_manager
from app.core.strategy.base_strategy import Signal


class BaseValidator(ABC):
    """Base class for risk validators."""

    @abstractmethod
    def validate(self, signal: Signal) -> tuple[bool, str]:
        """Return (approved, reason). reason is set on rejection."""
        ...


class CapitalAvailableValidator(BaseValidator):
    """Rejects BUY orders if insufficient capital."""

    def validate(self, signal: Signal) -> tuple[bool, str]:
        if signal.direction != Signal.BUY:
            return True, ""

        price = price_cache.get(signal.symbol)
        if price is None:
            return False, "No price available"

        required = Decimal(str(signal.quantity)) * Decimal(str(price))
        available = Decimal(str(portfolio_manager.capital))

        if required > available:
            return (
                False,
                f"Insufficient capital: need ₹{required:.2f}, have ₹{available:.2f}",
            )
        return True, ""


class MaxOpenPositionsValidator(BaseValidator):
    """Rejects BUY orders if max open positions limit is reached."""

    def __init__(self, max_positions: int = settings.max_open_positions) -> None:
        self.max_positions = max_positions

    def validate(self, signal: Signal) -> tuple[bool, str]:
        # SELL orders always pass — you should always be able to close
        if signal.direction != Signal.BUY:
            return True, ""

        current_count = len(portfolio_manager.positions)
        if current_count >= self.max_positions:
            return (
                False,
                f"Max open positions limit reached ({current_count}/{self.max_positions})",
            )
        return True, ""


class MaxDailyLossValidator(BaseValidator):
    """Rejects BUY orders if realized daily losses exceed threshold."""

    def __init__(
        self,
        max_loss_pct: float = settings.max_daily_loss_pct,
        initial_capital: float = settings.initial_capital,
    ) -> None:
        self.max_loss = Decimal(str(max_loss_pct)) * Decimal(str(initial_capital))

    def validate(self, signal: Signal) -> tuple[bool, str]:
        # SELL orders always pass
        if signal.direction != Signal.BUY:
            return True, ""

        daily_loss = Decimal(str(portfolio_manager.get_realized_daily_loss()))
        if daily_loss >= self.max_loss:
            return (
                False,
                f"Daily loss limit reached (₹{daily_loss:.2f} lost / ₹{self.max_loss:.2f} max)",
            )
        return True, ""


class RiskManager:
    """Runs all registered validators against a signal (short-circuit chain)."""

    def __init__(self) -> None:
        self._validators: list[BaseValidator] = []

    def add_validator(self, validator: BaseValidator) -> None:
        self._validators.append(validator)

    def check(self, signal: Signal) -> tuple[bool, str]:
        for validator in self._validators:
            approved, reason = validator.validate(signal)
            if not approved:
                return False, reason
        return True, ""


# Singleton with validators in order: Capital → MaxPositions → DailyLoss
risk_manager = RiskManager()
risk_manager.add_validator(CapitalAvailableValidator())
risk_manager.add_validator(MaxOpenPositionsValidator())
risk_manager.add_validator(MaxDailyLossValidator())
