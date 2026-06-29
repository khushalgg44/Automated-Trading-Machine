"""In-memory portfolio manager — tracks capital, positions, and trades.

Persists state to a JSON file periodically for restart recovery.
"""

import json
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.config import settings


class PortfolioManager:
    def __init__(self) -> None:
        self.capital: float = settings.initial_capital
        self.positions: dict[str, dict[str, Any]] = {}  # symbol -> {qty, avg_price}
        self.trades: list[dict[str, Any]] = []
        self._notes: dict[str, str] = {}  # trade_id -> note
        self._load_state()

    def reset(self) -> None:
        """Reset portfolio to initial state. Strategies keep running."""
        self.capital = settings.initial_capital
        self.positions = {}
        self.trades = []
        self._notes = {}
        self._save_state()

    def get_portfolio_summary(self) -> dict[str, Any]:
        return {
            "capital_available": round(self.capital, 2),
            "initial_capital": settings.initial_capital,
            "positions_count": len(self.positions),
            "total_trades": len(self.trades),
        }

    def get_positions(self) -> list[dict[str, Any]]:
        return [
            {"symbol": sym, **pos} for sym, pos in self.positions.items()
        ]

    def get_trades(self) -> list[dict[str, Any]]:
        return [
            {**t, "note": self._notes.get(str(t["id"]))} for t in self.trades
        ]

    def get_realized_daily_loss(self) -> float:
        """Calculate total realized losses for today.

        A loss occurs when a SELL trade's price is below the avg_price
        recorded at the time of the trade. We track this via 'pnl' field.
        """
        today = date.today().isoformat()
        total_loss = Decimal("0")

        for trade in self.trades:
            # Only count today's trades
            if not trade["timestamp"].startswith(today):
                continue
            pnl = trade.get("pnl", 0)
            if pnl < 0:
                total_loss += Decimal(str(abs(pnl)))

        return float(total_loss)

    def execute_buy(
        self, symbol: str, qty: int, price: float, strategy: str = ""
    ) -> dict[str, Any]:
        cost = Decimal(str(qty)) * Decimal(str(price))
        self.capital -= float(cost)

        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos["qty"] + qty
            avg = (
                Decimal(str(pos["avg_price"])) * Decimal(str(pos["qty"]))
                + Decimal(str(price)) * Decimal(str(qty))
            ) / Decimal(str(total_qty))
            pos["avg_price"] = float(avg.quantize(Decimal("0.01")))
            pos["qty"] = total_qty
        else:
            self.positions[symbol] = {"qty": qty, "avg_price": price}

        trade = {
            "id": len(self.trades) + 1,
            "symbol": symbol,
            "direction": "BUY",
            "qty": qty,
            "price": price,
            "value": float(cost.quantize(Decimal("0.01"))),
            "pnl": 0,
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
        }
        self.trades.append(trade)
        self._save_state()
        return trade

    def execute_sell(
        self, symbol: str, qty: int, price: float, strategy: str = ""
    ) -> dict[str, Any]:
        proceeds = Decimal(str(qty)) * Decimal(str(price))
        self.capital += float(proceeds)

        # Calculate PnL for this sell
        pnl = 0.0
        if symbol in self.positions:
            pos = self.positions[symbol]
            avg = Decimal(str(pos["avg_price"]))
            pnl_dec = (Decimal(str(price)) - avg) * Decimal(str(qty))
            pnl = float(pnl_dec.quantize(Decimal("0.01")))
            pos["qty"] -= qty
            if pos["qty"] <= 0:
                del self.positions[symbol]

        trade = {
            "id": len(self.trades) + 1,
            "symbol": symbol,
            "direction": "SELL",
            "qty": qty,
            "price": price,
            "value": float(proceeds.quantize(Decimal("0.01"))),
            "pnl": pnl,
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
        }
        self.trades.append(trade)
        self._save_state()
        return trade

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions and self.positions[symbol]["qty"] > 0

    def get_position_qty(self, symbol: str) -> int:
        if symbol in self.positions:
            return self.positions[symbol]["qty"]
        return 0

    def set_trade_note(self, trade_id: int, note: str) -> dict[str, Any] | None:
        """Add a note to a trade by ID."""
        self._notes[str(trade_id)] = note
        self._save_state()
        # Return the trade with note
        for t in self.trades:
            if t["id"] == trade_id:
                return {**t, "note": note}
        return None

    def _save_state(self) -> None:
        state = {
            "capital": self.capital,
            "positions": self.positions,
            "trades": self.trades,
            "notes": self._notes,
        }
        try:
            with open(settings.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _load_state(self) -> None:
        if not os.path.exists(settings.state_file):
            return
        try:
            with open(settings.state_file, "r") as f:
                state = json.load(f)
            self.capital = state.get("capital", settings.initial_capital)
            self.positions = state.get("positions", {})
            self.trades = state.get("trades", [])
            self._notes = state.get("notes", {})
        except Exception:
            pass


# Singleton
portfolio_manager = PortfolioManager()
