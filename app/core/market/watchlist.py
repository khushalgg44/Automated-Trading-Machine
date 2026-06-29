"""Watchlist — manages which symbols are actively being traded.

Strategies only process ticks for symbols in the watchlist.
Persists to state.json via portfolio manager.
"""

import json
import os
from typing import Any

from app.config import settings


class Watchlist:
    """Manages the active symbol watchlist."""

    def __init__(self) -> None:
        self._symbols: list[str] = list(settings.symbols)  # Default: RELIANCE, TCS, INFY
        self._load()

    @property
    def symbols(self) -> list[str]:
        return list(self._symbols)

    def add(self, symbol: str) -> bool:
        """Add a symbol to the watchlist. Returns False if already present or not in universe."""
        symbol = symbol.upper()
        if symbol not in settings.universe:
            return False
        if symbol in self._symbols:
            return False
        self._symbols.append(symbol)
        self._save()
        return True

    def remove(self, symbol: str) -> bool:
        """Remove a symbol from the watchlist."""
        symbol = symbol.upper()
        if symbol not in self._symbols:
            return False
        self._symbols.remove(symbol)
        self._save()
        return True

    def contains(self, symbol: str) -> bool:
        return symbol in self._symbols

    def _save(self) -> None:
        try:
            state = {}
            if os.path.exists("watchlist.json"):
                with open("watchlist.json", "r") as f:
                    state = json.load(f)
            state["watchlist"] = self._symbols
            with open("watchlist.json", "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    def _load(self) -> None:
        try:
            if os.path.exists("watchlist.json"):
                with open("watchlist.json", "r") as f:
                    state = json.load(f)
                self._symbols = state.get("watchlist", list(settings.symbols))
        except Exception:
            pass


# Singleton
watchlist = Watchlist()
