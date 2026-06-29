"""Tests for risk management validators."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from decimal import Decimal
from unittest.mock import patch

from app.core.strategy.base_strategy import Signal
from app.core.risk.manager import (
    CapitalAvailableValidator,
    MaxOpenPositionsValidator,
    MaxDailyLossValidator,
    RiskManager,
)


class TestCapitalAvailableValidator:
    def setup_method(self):
        self.validator = CapitalAvailableValidator()

    @patch("app.core.risk.manager.price_cache")
    @patch("app.core.risk.manager.portfolio_manager")
    def test_buy_rejected_insufficient_capital(self, mock_pm, mock_pc):
        mock_pc.get.return_value = 1000.0  # price per share
        mock_pm.capital = 500.0  # only ₹500 available

        signal = Signal(direction="BUY", symbol="TEST", quantity=10)  # needs ₹10,000
        approved, reason = self.validator.validate(signal)

        assert not approved
        assert "Insufficient capital" in reason

    @patch("app.core.risk.manager.price_cache")
    @patch("app.core.risk.manager.portfolio_manager")
    def test_buy_approved_sufficient_capital(self, mock_pm, mock_pc):
        mock_pc.get.return_value = 100.0
        mock_pm.capital = 50000.0

        signal = Signal(direction="BUY", symbol="TEST", quantity=10)  # needs ₹1,000
        approved, reason = self.validator.validate(signal)

        assert approved
        assert reason == ""

    @patch("app.core.risk.manager.price_cache")
    @patch("app.core.risk.manager.portfolio_manager")
    def test_sell_always_passes(self, mock_pm, mock_pc):
        mock_pm.capital = 0.0  # Even with no capital

        signal = Signal(direction="SELL", symbol="TEST", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert approved

    @patch("app.core.risk.manager.price_cache")
    def test_buy_rejected_no_price(self, mock_pc):
        mock_pc.get.return_value = None

        signal = Signal(direction="BUY", symbol="TEST", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert not approved
        assert "No price available" in reason


class TestMaxOpenPositionsValidator:
    def setup_method(self):
        self.validator = MaxOpenPositionsValidator(max_positions=3)

    @patch("app.core.risk.manager.portfolio_manager")
    def test_buy_rejected_at_limit(self, mock_pm):
        mock_pm.positions = {"A": {}, "B": {}, "C": {}}  # 3 positions = at limit

        signal = Signal(direction="BUY", symbol="D", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert not approved
        assert "Max open positions" in reason

    @patch("app.core.risk.manager.portfolio_manager")
    def test_buy_approved_below_limit(self, mock_pm):
        mock_pm.positions = {"A": {}, "B": {}}  # 2 positions, limit is 3

        signal = Signal(direction="BUY", symbol="C", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert approved

    @patch("app.core.risk.manager.portfolio_manager")
    def test_sell_always_passes_even_at_limit(self, mock_pm):
        mock_pm.positions = {"A": {}, "B": {}, "C": {}}

        signal = Signal(direction="SELL", symbol="A", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert approved


class TestMaxDailyLossValidator:
    def setup_method(self):
        # 5% of 100,000 = 5,000 max loss
        self.validator = MaxDailyLossValidator(max_loss_pct=0.05, initial_capital=100000.0)

    @patch("app.core.risk.manager.portfolio_manager")
    def test_buy_rejected_loss_exceeded(self, mock_pm):
        mock_pm.get_realized_daily_loss.return_value = 6000.0  # > 5000 limit

        signal = Signal(direction="BUY", symbol="TEST", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert not approved
        assert "Daily loss limit" in reason

    @patch("app.core.risk.manager.portfolio_manager")
    def test_buy_approved_loss_within_limit(self, mock_pm):
        mock_pm.get_realized_daily_loss.return_value = 2000.0  # < 5000

        signal = Signal(direction="BUY", symbol="TEST", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert approved

    @patch("app.core.risk.manager.portfolio_manager")
    def test_sell_always_passes(self, mock_pm):
        mock_pm.get_realized_daily_loss.return_value = 99999.0

        signal = Signal(direction="SELL", symbol="TEST", quantity=10)
        approved, reason = self.validator.validate(signal)

        assert approved


class TestRiskManagerChain:
    @patch("app.core.risk.manager.price_cache")
    @patch("app.core.risk.manager.portfolio_manager")
    def test_chain_short_circuits_on_first_failure(self, mock_pm, mock_pc):
        """If first validator rejects, second is never called."""
        mock_pc.get.return_value = 1000.0
        mock_pm.capital = 100.0  # Can't afford

        rm = RiskManager()
        rm.add_validator(CapitalAvailableValidator())
        rm.add_validator(MaxOpenPositionsValidator(max_positions=5))

        signal = Signal(direction="BUY", symbol="TEST", quantity=10)
        approved, reason = rm.check(signal)

        assert not approved
        assert "Insufficient capital" in reason  # First validator's reason
