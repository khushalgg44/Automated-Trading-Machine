"""Analytics module — computes trading performance metrics from trades list."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def compute_analytics(trades: list[dict[str, Any]], initial_capital: float) -> dict[str, str]:
    """Compute performance metrics from a list of trades.

    Returns all values as strings with Decimal precision.
    """
    total_trades = len(trades)

    # Only SELL trades with non-zero PnL count as closed trades for win/loss
    closed_trades = [t for t in trades if t["direction"] == "SELL" and t.get("pnl", 0) != 0]
    winning_trades = [t for t in closed_trades if t["pnl"] > 0]
    losing_trades = [t for t in closed_trades if t["pnl"] < 0]

    # Win rate
    if closed_trades:
        win_rate = Decimal(len(winning_trades)) / Decimal(len(closed_trades)) * Decimal("100")
    else:
        win_rate = Decimal("0")

    # Average profit/loss
    if winning_trades:
        total_profit = sum(Decimal(str(t["pnl"])) for t in winning_trades)
        avg_profit = total_profit / Decimal(len(winning_trades))
    else:
        total_profit = Decimal("0")
        avg_profit = Decimal("0")

    if losing_trades:
        total_loss = sum(Decimal(str(abs(t["pnl"]))) for t in losing_trades)
        avg_loss = total_loss / Decimal(len(losing_trades))
    else:
        total_loss = Decimal("0")
        avg_loss = Decimal("0")

    # Profit factor
    if total_loss > 0:
        profit_factor = total_profit / total_loss
        profit_factor_str = str(profit_factor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    else:
        profit_factor_str = "∞" if total_profit > 0 else "0.00"

    # Max drawdown — track peak equity and compute largest drop
    equity = Decimal(str(initial_capital))
    peak = equity
    max_dd = Decimal("0")

    for trade in trades:
        if trade["direction"] == "BUY":
            equity -= Decimal(str(trade["value"]))
        else:
            equity += Decimal(str(trade["value"]))

        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    # Best and worst trades (by PnL)
    best_pnl = Decimal("0")
    worst_pnl = Decimal("0")
    best_pct = Decimal("0")
    worst_pct = Decimal("0")

    for t in closed_trades:
        pnl = Decimal(str(t["pnl"]))
        trade_value = Decimal(str(t["qty"])) * Decimal(str(t["price"]))
        pct = (pnl / trade_value * Decimal("100")) if trade_value > 0 else Decimal("0")

        if pnl > best_pnl:
            best_pnl = pnl
            best_pct = pct
        if pnl < worst_pnl:
            worst_pnl = pnl
            worst_pct = pct

    return {
        "total_trades": str(total_trades),
        "win_rate": str(win_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "avg_profit": str(avg_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "avg_loss": str(avg_loss.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "profit_factor": profit_factor_str,
        "max_drawdown": str(max_dd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "best_trade": str(best_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "best_trade_pct": str(best_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "worst_trade": str(worst_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "worst_trade_pct": str(worst_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
    }
