"""Backtesting engine — replays historical candles through a strategy.

Completely isolated from the live trading system. Creates its own
portfolio, positions, and risk validators. Uses the same strategy classes.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.config import settings
from app.core.strategy.base_strategy import Signal
from app.core.strategy.ema_cross import EMACrossStrategy
from app.core.strategy.rsi_mean_reversion import RSIMeanReversionStrategy
from app.core.strategy.bollinger_bands import BollingerBandsStrategy


class BacktestPortfolio:
    """Lightweight isolated portfolio for backtest — no persistence, no events."""

    def __init__(self, initial_capital: float) -> None:
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: dict[str, dict[str, Any]] = {}
        self.trades: list[dict[str, Any]] = []

    def execute_buy(self, symbol: str, qty: int, price: float, timestamp: str = "") -> dict[str, Any]:
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
            "pnl": 0.0,
            "timestamp": timestamp,
        }
        self.trades.append(trade)
        return trade

    def execute_sell(self, symbol: str, qty: int, price: float, timestamp: str = "") -> dict[str, Any]:
        proceeds = Decimal(str(qty)) * Decimal(str(price))
        self.capital += float(proceeds)

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
            "timestamp": timestamp,
        }
        self.trades.append(trade)
        return trade


class BacktestRiskManager:
    """Simplified risk check for backtest — only capital + max positions."""

    def check(self, signal: Signal, portfolio: BacktestPortfolio, price: float) -> tuple[bool, str]:
        if signal.direction == Signal.BUY:
            required = Decimal(str(signal.quantity)) * Decimal(str(price))
            available = Decimal(str(portfolio.capital))
            if required > available:
                return False, "Insufficient capital"
            if len(portfolio.positions) >= settings.max_open_positions:
                return False, "Max positions reached"
        return True, ""


def _create_strategy(strategy_name: str):
    """Create a fresh isolated strategy instance for backtesting."""
    if strategy_name == "ema_cross":
        return EMACrossStrategy(
            fast_period=settings.ema_fast_period,
            slow_period=settings.ema_slow_period,
            qty=10,
        )
    elif strategy_name == "rsi_mean_reversion":
        return RSIMeanReversionStrategy(
            period=settings.rsi_period,
            oversold=settings.rsi_oversold,
            overbought=settings.rsi_overbought,
            qty=10,
        )
    elif strategy_name == "bollinger_bands":
        return BollingerBandsStrategy(
            period=settings.bb_period,
            std_dev_multiplier=settings.bb_std_dev,
            qty=10,
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")


async def run_backtest(
    strategy_name: str,
    symbol: str,
    candles: list[dict[str, Any]],
    initial_capital: float = settings.initial_capital,
) -> dict[str, Any]:
    """Run a complete backtest.

    Creates isolated portfolio, strategy, and risk manager.
    Replays each candle's close as a tick through the strategy.
    Returns full results. Runs within the existing asyncio event loop.
    """
    portfolio = BacktestPortfolio(initial_capital)
    risk = BacktestRiskManager()
    strategy = _create_strategy(strategy_name)

    # Manually activate the strategy (don't subscribe to event bus)
    strategy._active = True

    equity_curve: list[dict[str, Any]] = []
    current_price = 0.0

    def _calc_equity() -> float:
        eq = portfolio.capital
        for sym, pos in portfolio.positions.items():
            eq += pos["qty"] * current_price
        return round(eq, 2)

    for i, candle in enumerate(candles):
        current_price = candle["close"]
        timestamp = candle.get("date", str(i))

        tick_payload = {
            "symbol": symbol,
            "ltp": current_price,
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": current_price,
            "volume": candle["volume"],
            "timestamp": timestamp,
        }

        # Call strategy's on_tick (async method)
        signal = await strategy.on_tick(tick_payload)

        if signal:
            # Risk check
            approved, _ = risk.check(signal, portfolio, current_price)
            if approved:
                if signal.direction == Signal.BUY:
                    portfolio.execute_buy(symbol, signal.quantity, current_price, timestamp)
                elif signal.direction == Signal.SELL:
                    portfolio.execute_sell(symbol, signal.quantity, current_price, timestamp)

        # Record equity after this candle
        eq = _calc_equity()
        equity_curve.append({"candle": i + 1, "date": timestamp, "equity": eq})

    # Compute results
    final_equity = _calc_equity()
    total_return_pct = ((Decimal(str(final_equity)) - Decimal(str(initial_capital)))
                        / Decimal(str(initial_capital)) * Decimal("100"))

    # Win rate from closed trades
    closed = [t for t in portfolio.trades if t["direction"] == "SELL" and t["pnl"] != 0]
    winners = [t for t in closed if t["pnl"] > 0]
    win_rate = (Decimal(len(winners)) / Decimal(len(closed)) * Decimal("100")) if closed else Decimal("0")

    # Max drawdown
    peak = Decimal(str(initial_capital))
    max_dd = Decimal("0")
    for point in equity_curve:
        eq = Decimal(str(point["equity"]))
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    return {
        "strategy": strategy_name,
        "symbol": symbol,
        "candles_processed": len(candles),
        "final_equity": str(Decimal(str(final_equity)).quantize(Decimal("0.01"))),
        "total_return_pct": str(total_return_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "total_trades": len(portfolio.trades),
        "win_rate": str(win_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "max_drawdown": str(max_dd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "trades": portfolio.trades,
        "equity_curve": equity_curve,
    }
