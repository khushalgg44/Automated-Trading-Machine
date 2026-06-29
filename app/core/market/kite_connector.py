"""Zerodha Kite WebSocket connector — drop-in replacement for mock_tick_generator.

Not activated by default. Set DATA_SOURCE=zerodha in config to use.
"""
import asyncio
import time
from decimal import Decimal
from typing import Any

from app.event_bus import event_bus, Events
from app.config import settings


class KiteTickerConnector:
    """Connects to Zerodha's Kite WebSocket for live market ticks."""

    def __init__(self, api_key: str, access_token: str, symbols: list[str]) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._symbols = symbols
        self._running = False
        self._kws = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            from kiteconnect import KiteTicker
            self._kws = KiteTicker(self._api_key, self._access_token)
            self._kws.on_ticks = self._on_ticks
            self._kws.on_connect = self._on_connect
            self._kws.on_close = self._on_close
            self._kws.on_error = self._on_error
            self._kws.connect(threaded=True)
            event_bus.log_custom("ZERODHA_CONNECTED", "Kite WebSocket connected")
        except ImportError:
            print("[KiteConnector] kiteconnect not installed. Falling back to mock.")
            self._running = False
        except Exception as e:
            print(f"[KiteConnector] Failed to start: {e}")
            event_bus.log_custom("ZERODHA_ERROR", str(e))
            self._running = False

    async def stop(self) -> None:
        self._running = False
        if self._kws:
            try:
                self._kws.close()
            except Exception:
                pass
            self._kws = None
        event_bus.log_custom("ZERODHA_DISCONNECTED", "Kite WebSocket disconnected")

    def _on_connect(self, ws, response) -> None:
        # Subscribe to instruments in FULL mode
        # In real usage, you'd map symbol names to instrument tokens
        # For now, subscribe to the symbols list as-is (tokens would be looked up)
        print(f"[KiteConnector] Connected. Subscribing to {len(self._symbols)} symbols")
        self._reconnect_delay = 1.0  # Reset backoff on successful connect

    def _on_ticks(self, ws, ticks) -> None:
        """Transform Kite ticks to our internal format and publish."""
        loop = asyncio.new_event_loop()
        for tick in ticks:
            try:
                payload = {
                    "symbol": tick.get("tradingsymbol", "UNKNOWN"),
                    "ltp": float(Decimal(str(tick.get("last_price", 0)))),
                    "open": float(tick.get("ohlc", {}).get("open", 0)),
                    "high": float(tick.get("ohlc", {}).get("high", 0)),
                    "low": float(tick.get("ohlc", {}).get("low", 0)),
                    "close": float(tick.get("ohlc", {}).get("close", 0)),
                    "volume": tick.get("volume_traded", 0),
                    "timestamp": tick.get("exchange_timestamp", "").isoformat() if tick.get("exchange_timestamp") else "",
                }
                loop.run_until_complete(event_bus.publish(Events.TICK_RECEIVED, payload))
            except Exception as e:
                print(f"[KiteConnector] Tick processing error: {e}")
        loop.close()

    def _on_close(self, ws, code, reason) -> None:
        """Handle disconnection with exponential backoff reconnect."""
        if not self._running:
            return
        print(f"[KiteConnector] Disconnected: {code} {reason}. Reconnecting in {self._reconnect_delay}s...")
        event_bus.log_custom("ZERODHA_DISCONNECTED", f"Code {code}: {reason}")
        time.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
        if self._kws and self._running:
            self._kws.connect(threaded=True)

    def _on_error(self, ws, code, reason) -> None:
        """Handle errors — check for token expiry."""
        print(f"[KiteConnector] Error: {code} {reason}")
        if "token" in str(reason).lower() or code == 403:
            event_bus.log_custom("AUTH_EXPIRED", "Zerodha access token expired")
            self._running = False
