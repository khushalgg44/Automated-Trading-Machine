"""Telegram bot notification service (placeholder).

To activate:
1. Create a bot via @BotFather on Telegram
2. Get the bot token
3. Add ALGOTRADEX_TELEGRAM_BOT_TOKEN and ALGOTRADEX_TELEGRAM_CHAT_ID to .env
4. Set ALGOTRADEX_TELEGRAM_ENABLED=true
"""

import os
from typing import Any

TELEGRAM_ENABLED = os.getenv("ALGOTRADEX_TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("ALGOTRADEX_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("ALGOTRADEX_TELEGRAM_CHAT_ID", "")


async def send_telegram(message: str) -> bool:
    """Send a message via Telegram bot. Returns True if sent."""
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        import httpx
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
            return resp.status_code == 200
    except Exception:
        return False


async def notify_trade(trade: dict[str, Any]) -> None:
    """Send trade notification."""
    msg = f"🔔 <b>{trade.get('direction', '')} {trade.get('symbol', '')}</b>\n"
    msg += f"Qty: {trade.get('qty', 0)} @ ₹{trade.get('price', 0):.2f}\n"
    msg += f"Strategy: {trade.get('strategy', 'manual')}"
    if trade.get('pnl', 0) != 0:
        pnl = trade['pnl']
        emoji = "📈" if pnl > 0 else "📉"
        msg += f"\nP&L: {emoji} ₹{pnl:.2f}"
    await send_telegram(msg)


async def notify_rejection(detail: str) -> None:
    """Send rejection notification."""
    await send_telegram(f"⚠️ <b>Order Rejected</b>\n{detail}")
