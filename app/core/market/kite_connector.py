"""Zerodha Kite WebSocket connector — drop-in replacement for mock_tick_generator.

Connects to Kite's WebSocket ticker for real-time NSE market data.
Publishes TICK_RECEIVED events through the same EventBus as the mock generator.
"""

import asyncio
import threading
import time
from decimal import Decimal
from typing import Any

from app.config import settings
from app.event_bus import event_bus, Events
from app.core.market.watchlist import watchlist


class KiteTickerConnector:
    """Connects to Zerodha's Kite WebSocket for live market ticks."""

    def __init__(self, api_key: str, access_token: str) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._running = False
        self._kws = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0
        # symbol name → instrument token mapping
        self._token_map: dict[int, str] = {}  # token → symbol
        self._symbol_tokens: dict[str, int] = {}  # symbol → token

    @property
    def is_running(self) -> bool:
        return self._running

    def _fetch_instrument_tokens(self) -> None:
        """Fetch NSE instrument list and map watchlist symbols to tokens."""
        try:
            import requests as req
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Fetch instruments directly via REST (bypass kiteconnect SSL)
            headers = {"Authorization": f"token {self._api_key}:{self._access_token}"}
            resp = req.get(
                "https://api.kite.trade/instruments/NSE",
                headers=headers,
                verify=False,
            )

            if resp.status_code != 200:
                print(f"[KiteConnector] Instruments fetch failed: {resp.status_code}")
                return

            # Parse CSV response
            import csv
            import io
            reader = csv.DictReader(io.StringIO(resp.text))
            nse_lookup: dict[str, int] = {}
            for row in reader:
                nse_lookup[row["tradingsymbol"]] = int(row["instrument_token"])

            # Map our universe symbols to tokens
            for symbol in settings.universe:
                token = nse_lookup.get(symbol)
                if token:
                    self._symbol_tokens[symbol] = token
                    self._token_map[token] = symbol

            print(f"[KiteConnector] Mapped {len(self._symbol_tokens)} symbols to instrument tokens")
        except Exception as e:
            print(f"[KiteConnector] Failed to fetch instruments: {e}")

    async def start(self) -> None:
        """Start the Kite WebSocket connection."""
        if self._running:
            return

        self._loop = asyncio.get_event_loop()

        # Fetch instrument tokens
        self._fetch_instrument_tokens()
        if not self._symbol_tokens:
            print("[KiteConnector] No instrument tokens found. Cannot start.")
            event_bus.log_custom("ZERODHA_ERROR", "No instrument tokens found")
            return

        self._running = True

        try:
            from kiteconnect import KiteTicker

            self._kws = KiteTicker(self._api_key, self._access_token)
            self._kws.on_ticks = self._on_ticks
            self._kws.on_connect = self._on_connect
            self._kws.on_close = self._on_close
            self._kws.on_error = self._on_error

            # Run WebSocket in a separate thread (it's blocking)
            self._kws.connect(threaded=True)
            event_bus.log_custom("ZERODHA_CONNECTED", f"Kite WebSocket started with {len(self._symbol_tokens)} instruments")
            print(f"[KiteConnector] WebSocket connected. Subscribed to {len(self._symbol_tokens)} symbols.")
        except ImportError:
            print("[KiteConnector] kiteconnect not installed.")
            self._running = False
        except Exception as e:
            print(f"[KiteConnector] Failed to start: {e}")
            event_bus.log_custom("ZERODHA_ERROR", str(e))
            self._running = False

    async def stop(self) -> None:
        """Stop the WebSocket connection."""
        self._running = False
        if self._kws:
            try:
                self._kws.close()
            except Exception:
                pass
            self._kws = None
        event_bus.log_custom("ZERODHA_DISCONNECTED", "Kite WebSocket stopped")

    def _on_connect(self, ws, response) -> None:
        """Subscribe to instruments in FULL mode on connect."""
        # Only subscribe to watchlist symbols (not all universe)
        tokens_to_subscribe = [
            self._symbol_tokens[sym]
            for sym in watchlist.symbols
            if sym in self._symbol_tokens
        ]
        if tokens_to_subscribe:
            ws.subscribe(tokens_to_subscribe)
            ws.set_mode(ws.MODE_FULL, tokens_to_subscribe)
            print(f"[KiteConnector] Subscribed to {len(tokens_to_subscribe)} instruments in FULL mode")
        self._reconnect_delay = 1.0  # Reset backoff

    def _on_ticks(self, ws, ticks) -> None:
        """Transform Kite ticks to our internal format and publish on EventBus."""
        if not self._loop or not self._running:
            return

        for tick in ticks:
            try:
                instrument_token = tick.get("instrument_token")
                symbol = self._token_map.get(instrument_token, "UNKNOWN")

                if symbol == "UNKNOWN":
                    continue

                ohlc = tick.get("ohlc", {})
                payload = {
                    "symbol": symbol,
                    "ltp": float(Decimal(str(tick.get("last_price", 0)))),
                    "open": float(ohlc.get("open", 0)),
                    "high": float(ohlc.get("high", 0)),
                    "low": float(ohlc.get("low", 0)),
                    "close": float(ohlc.get("close", 0)),
                    "volume": tick.get("volume_traded", 0),
                    "timestamp": tick.get("exchange_timestamp", "").isoformat()
                    if tick.get("exchange_timestamp")
                    else "",
                }

                # Schedule async publish on the main event loop
                asyncio.run_coroutine_threadsafe(
                    event_bus.publish(Events.TICK_RECEIVED, payload),
                    self._loop,
                )
            except Exception as e:
                print(f"[KiteConnector] Tick error: {e}")

    def _on_close(self, ws, code, reason) -> None:
        """Handle disconnection with exponential backoff."""
        if not self._running:
            return
        print(f"[KiteConnector] Disconnected: {code} {reason}. Reconnecting in {self._reconnect_delay}s...")
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._log_async("ZERODHA_DISCONNECTED", f"Code {code}: {reason}"),
                self._loop,
            )
        time.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    def _on_error(self, ws, code, reason) -> None:
        """Handle errors — detect token expiry."""
        print(f"[KiteConnector] Error: {code} {reason}")
        if "token" in str(reason).lower() or code == 403:
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._log_async("AUTH_EXPIRED", "Zerodha access token expired"),
                    self._loop,
                )
            self._running = False

    async def _log_async(self, event: str, detail: str) -> None:
        event_bus.log_custom(event, detail)
