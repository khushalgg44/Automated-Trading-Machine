"""Telegram bot — sends trade alerts and accepts commands.

Hooks into EventBus for ORDER_FILLED and ORDER_REJECTED notifications.
"""

import os
import asyncio
import threading
from typing import Any

from app.event_bus import event_bus, Events

TELEGRAM_ENABLED = os.getenv("ALGOTRADEX_TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("ALGOTRADEX_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("ALGOTRADEX_TELEGRAM_CHAT_ID", "")


async def send_telegram(message: str) -> bool:
    """Send a message via Telegram bot."""
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        import httpx
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            })
            return resp.status_code == 200
    except Exception as e:
        print(f"[Telegram] Send failed: {e}")
        return False


async def _on_order_filled(payload: dict[str, Any]) -> None:
    """Notify on every trade fill."""
    direction = payload.get("direction", "")
    symbol = payload.get("symbol", "")
    qty = payload.get("qty", 0)
    price = payload.get("price", 0)
    strategy = payload.get("strategy", "")
    pnl = payload.get("pnl", 0)

    emoji = "🟢" if direction == "BUY" else "🔴"
    msg = f"{emoji} <b>{direction} {symbol}</b> x{qty} @ ₹{price:.2f}\n"
    msg += f"Strategy: {strategy}"
    if pnl and pnl != 0:
        pnl_emoji = "📈" if pnl > 0 else "📉"
        msg += f"\nP&L: {pnl_emoji} ₹{pnl:.2f}"

    await send_telegram(msg)


async def _on_order_rejected(payload: dict[str, Any]) -> None:
    """Notify on rejections."""
    detail = payload.get("detail", str(payload))
    # The event log stores detail as a string in the custom log
    await send_telegram(f"⚠️ <b>Order Rejected</b>\n{detail}")


def start_telegram_bot() -> None:
    """Subscribe to events and start polling for commands."""
    if not TELEGRAM_ENABLED:
        return

    # Subscribe to trade events
    event_bus.subscribe(Events.ORDER_FILLED, _on_order_filled)
    print(f"[Telegram] Bot enabled. Sending alerts to chat {TELEGRAM_CHAT_ID}")

    # Start command polling in background
    _poll_thread = threading.Thread(target=_poll_commands, daemon=True)
    _poll_thread.start()


def _poll_commands() -> None:
    """Poll for incoming Telegram commands in a background thread."""
    import time
    try:
        import httpx
    except ImportError:
        print("[Telegram] httpx not installed, command polling disabled")
        return

    last_update_id = 0
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    while True:
        try:
            with httpx.Client(verify=False, timeout=30) as client:
                resp = client.get(f"{base_url}/getUpdates", params={
                    "offset": last_update_id + 1,
                    "timeout": 20,
                })
                if resp.status_code != 200:
                    time.sleep(5)
                    continue

                data = resp.json()
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip()
                    chat_id = str(msg.get("chat", {}).get("id", ""))

                    if chat_id != TELEGRAM_CHAT_ID:
                        continue

                    # Handle commands
                    response = _handle_command(text)
                    if response:
                        with httpx.Client(verify=False) as c:
                            c.post(f"{base_url}/sendMessage", json={
                                "chat_id": TELEGRAM_CHAT_ID,
                                "text": response,
                                "parse_mode": "HTML",
                            })

        except Exception as e:
            print(f"[Telegram] Poll error: {e}")
            time.sleep(5)


def _handle_command(text: str) -> str | None:
    """Process incoming commands and return response text."""
    if not text.startswith("/"):
        return None

    cmd = text.lower().split()[0]

    if cmd == "/start" or cmd == "/help":
        return (
            "🤖 <b>AlgoTradeX Bot</b>\n\n"
            "Commands:\n"
            "/status — Portfolio summary\n"
            "/positions — Open positions\n"
            "/pnl — Today's P&L\n"
            "/trades — Recent trades\n"
            "/strategies — Strategy status"
        )

    if cmd == "/status":
        from app.core.trading.portfolio_manager import portfolio_manager
        summary = portfolio_manager.get_portfolio_summary()
        return (
            f"📊 <b>Portfolio Status</b>\n"
            f"Capital: ₹{summary['capital_available']:,.2f}\n"
            f"Positions: {summary['positions_count']}\n"
            f"Total Trades: {summary['total_trades']}"
        )

    if cmd == "/positions":
        from app.core.trading.portfolio_manager import portfolio_manager
        positions = portfolio_manager.get_positions()
        if not positions:
            return "📭 No open positions"
        lines = ["📈 <b>Open Positions</b>\n"]
        for p in positions:
            lines.append(f"• {p['symbol']}: {p['qty']} @ ₹{p['avg_price']:.2f}")
        return "\n".join(lines)

    if cmd == "/pnl":
        from app.core.trading.portfolio_manager import portfolio_manager
        summary = portfolio_manager.get_portfolio_summary()
        pnl = summary["capital_available"] - summary["initial_capital"]
        emoji = "📈" if pnl >= 0 else "📉"
        return f"{emoji} <b>Today's P&L</b>\n₹{pnl:+,.2f}"

    if cmd == "/trades":
        from app.core.trading.portfolio_manager import portfolio_manager
        trades = portfolio_manager.get_trades()
        recent = trades[-5:] if trades else []
        if not recent:
            return "📭 No trades yet"
        lines = ["📋 <b>Last 5 Trades</b>\n"]
        for t in reversed(recent):
            emoji = "🟢" if t["direction"] == "BUY" else "🔴"
            lines.append(f"{emoji} {t['direction']} {t['symbol']} x{t['qty']} @ ₹{t['price']:.2f}")
        return "\n".join(lines)

    if cmd == "/strategies":
        from app.core.strategy.registry import strategy_registry
        names = strategy_registry.list_all()
        lines = ["⚙️ <b>Strategies</b>\n"]
        for n in names:
            s = strategy_registry.get(n)
            status = "🟢 RUNNING" if s.is_active else "⚪ STOPPED"
            lines.append(f"• {n}: {status}")
        return "\n".join(lines)

    return None
