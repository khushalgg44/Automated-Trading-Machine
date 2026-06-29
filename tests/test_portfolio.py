"""Tests for portfolio manager — capital, positions, PnL."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from decimal import Decimal
from unittest.mock import patch

from app.config import settings


# Use a fresh PortfolioManager for each test (not the singleton)
class TestPortfolioManager:
    def _make_pm(self):
        """Create a fresh PortfolioManager without loading state."""
        with patch("app.core.trading.portfolio_manager.os.path.exists", return_value=False):
            from app.core.trading.portfolio_manager import PortfolioManager
            pm = PortfolioManager()
        return pm

    def test_initial_state(self):
        pm = self._make_pm()
        assert pm.capital == settings.initial_capital
        assert pm.positions == {}
        assert pm.trades == []

    def test_buy_decreases_capital(self):
        pm = self._make_pm()
        initial = pm.capital
        pm.execute_buy("TEST", qty=10, price=100.0)

        expected_cost = Decimal("10") * Decimal("100.0")
        assert Decimal(str(pm.capital)) == Decimal(str(initial)) - expected_cost

    def test_buy_creates_position(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)

        assert "TEST" in pm.positions
        assert pm.positions["TEST"]["qty"] == 10
        assert pm.positions["TEST"]["avg_price"] == 100.0

    def test_buy_averages_position(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)
        pm.execute_buy("TEST", qty=10, price=120.0)

        assert pm.positions["TEST"]["qty"] == 20
        # Avg = (100*10 + 120*10) / 20 = 110
        assert pm.positions["TEST"]["avg_price"] == 110.0

    def test_sell_increases_capital(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)
        capital_after_buy = pm.capital

        pm.execute_sell("TEST", qty=10, price=110.0)
        proceeds = Decimal("10") * Decimal("110.0")
        assert Decimal(str(pm.capital)) == Decimal(str(capital_after_buy)) + proceeds

    def test_sell_closes_position(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)
        pm.execute_sell("TEST", qty=10, price=110.0)

        assert "TEST" not in pm.positions

    def test_sell_partial_keeps_position(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)
        pm.execute_sell("TEST", qty=5, price=110.0)

        assert pm.positions["TEST"]["qty"] == 5

    def test_pnl_calculation_profit(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)
        trade = pm.execute_sell("TEST", qty=10, price=110.0)

        # PnL = (110 - 100) * 10 = 100
        assert Decimal(str(trade["pnl"])) == Decimal("100.00")

    def test_pnl_calculation_loss(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)
        trade = pm.execute_sell("TEST", qty=10, price=95.0)

        # PnL = (95 - 100) * 10 = -50
        assert Decimal(str(trade["pnl"])) == Decimal("-50.00")

    def test_reset_restores_initial_state(self):
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=10, price=100.0)
        pm.execute_sell("TEST", qty=10, price=110.0)

        pm.reset()

        assert pm.capital == settings.initial_capital
        assert pm.positions == {}
        assert pm.trades == []

    def test_trade_records_strategy(self):
        pm = self._make_pm()
        trade = pm.execute_buy("TEST", qty=5, price=200.0, strategy="ema_cross")
        assert trade["strategy"] == "ema_cross"

    def test_no_float_contamination_in_pnl(self):
        """Verify PnL uses Decimal math — no floating point issues."""
        pm = self._make_pm()
        pm.execute_buy("TEST", qty=3, price=33.33)
        trade = pm.execute_sell("TEST", qty=3, price=33.34)

        # PnL should be exactly 0.03, not something like 0.030000000000001
        pnl = Decimal(str(trade["pnl"]))
        assert pnl == Decimal("0.03")
