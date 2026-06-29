"""Simple in-process async event bus.

Any component can publish events; any component can subscribe.
The mock tick generator and real Zerodha WebSocket both publish
TICK_RECEIVED — downstream consumers don't know the difference.
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Callable, Coroutine

# Type alias for an async event handler
Handler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

# Max events to retain for the event log
_MAX_EVENT_LOG = 200


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._event_log: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENT_LOG)
        self._total_ticks: int = 0
        self._total_events: int = 0
        self._tick_times: deque[float] = deque(maxlen=100)  # timestamps of recent ticks
        self._last_tick_time: str | None = None

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self._total_events += 1

        # Track tick metrics
        if event_type == Events.TICK_RECEIVED:
            self._total_ticks += 1
            import time
            self._tick_times.append(time.time())
            self._last_tick_time = datetime.now().isoformat()
        else:
            # Log non-tick events
            self._event_log.append({
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "detail": _summarize(event_type, payload),
            })

        for handler in self._subscribers.get(event_type, []):
            try:
                await handler(payload)
            except Exception as exc:
                # Log but don't crash the bus
                print(f"[EventBus] handler error on {event_type}: {exc}")

    async def publish_nowait(self, event_type: str, payload: dict[str, Any]) -> None:
        """Fire-and-forget: schedule handlers as tasks."""
        for handler in self._subscribers.get(event_type, []):
            asyncio.create_task(handler(payload))

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the last N logged events (excludes TICK_RECEIVED)."""
        items = list(self._event_log)
        return items[-limit:]

    def log_custom(self, event_type: str, detail: str) -> None:
        """Manually log a custom event (e.g. RISK_VIOLATION)."""
        self._event_log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "detail": detail,
        })

    def clear_log(self) -> None:
        """Clear the event log (used on portfolio reset)."""
        self._event_log.clear()

    def get_tick_stats(self) -> dict[str, Any]:
        """Return tick rate and total tick stats."""
        import time
        now = time.time()
        # Count ticks in last 10 seconds
        recent = [t for t in self._tick_times if now - t <= 10.0]
        tps = len(recent) / 10.0 if recent else 0.0
        return {
            "total_ticks": self._total_ticks,
            "total_events": self._total_events,
            "ticks_per_second": round(tps, 1),
            "last_tick_time": self._last_tick_time,
        }


def _summarize(event_type: str, payload: dict[str, Any]) -> str:
    """Create a brief human-readable summary for the event log."""
    if event_type == Events.SIGNAL_GENERATED:
        sig = payload.get("signal")
        strategy = payload.get("strategy", "")
        prefix = f"[{strategy}] " if strategy else ""
        if sig:
            return f"{prefix}{sig.direction} {sig.symbol} x{sig.quantity} — {sig.reason}"
        return str(payload)
    if event_type == Events.ORDER_FILLED:
        strategy = payload.get("strategy", "")
        prefix = f"[{strategy}] " if strategy else ""
        return f"{prefix}{payload.get('direction', '')} {payload.get('symbol', '')} x{payload.get('qty', '')} @ ₹{payload.get('price', '')}"
    if event_type == Events.ORDER_PLACED:
        return str(payload.get("detail", payload))
    if event_type == Events.STRATEGY_STARTED:
        return str(payload.get("detail", payload))
    if event_type == Events.STRATEGY_STOPPED:
        return str(payload.get("detail", payload))
    return str(payload)[:120]


# Singleton instance shared across the app
event_bus = EventBus()


# Standard event type constants
class Events:
    TICK_RECEIVED = "TICK_RECEIVED"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    POSITION_UPDATED = "POSITION_UPDATED"
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    PORTFOLIO_RESET = "PORTFOLIO_RESET"
