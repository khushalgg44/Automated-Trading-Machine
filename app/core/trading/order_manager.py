"""Order manager — bridges strategy signals to the paper engine via risk checks.

Flow: SIGNAL_GENERATED → Risk Manager check → Paper Engine fill → portfolio update.
"""

from typing import Any

from app.event_bus import event_bus, Events
from app.core.market.price_cache import price_cache
from app.core.risk.manager import risk_manager
from app.core.trading.paper_engine import paper_engine
from app.core.trading.order_log import order_log
from app.core.strategy.base_strategy import Signal
from app.core.logger import get_logger

logger = get_logger("trading.order_manager")


class OrderManager:
    def __init__(self) -> None:
        event_bus.subscribe(Events.SIGNAL_GENERATED, self._on_signal)

    async def _on_signal(self, payload: dict[str, Any]) -> None:
        signal: Signal = payload["signal"]
        strategy_name: str = payload.get("strategy", "")

        # Run risk checks
        approved, reason = risk_manager.check(signal)
        if not approved:
            event_bus.log_custom(
                Events.ORDER_REJECTED,
                f"[{strategy_name}] {signal.direction} {signal.symbol} x{signal.quantity}: {reason}",
            )
            # Log to order tape
            current_price = price_cache.get(signal.symbol) or 0
            order_log.log_rejection(
                signal.symbol, signal.direction, signal.quantity,
                current_price, strategy_name, reason,
            )
            return

        # Fill via paper engine
        trade = await paper_engine.fill_order(signal, strategy=strategy_name)
        if trade:
            logger.info(
                f"FILLED {trade['direction']} {trade['qty']}x "
                f"{trade['symbol']} @ ₹{trade['price']:.2f} [{strategy_name}]"
            )


# Singleton — subscribes on import
order_manager = OrderManager()
