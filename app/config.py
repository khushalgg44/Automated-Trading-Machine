"""Application configuration — all tunables in one place.

Loads from environment variables (prefix ALGOTRADEX_) and .env file.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env file from project root
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path)


class Settings(BaseModel):
    model_config = {"env_prefix": "ALGOTRADEX_"}

    # Portfolio
    initial_capital: float = 10_00_000.0  # ₹10 lakh

    # Mock tick generator
    symbols: list[str] = ["RELIANCE", "TCS", "INFY"]
    universe: list[str] = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "WIPRO", "ICICIBANK", "BHARTIARTL"]
    tick_interval_ms: int = 100  # delay between ticks in mock mode
    speed_multiplier: float = 60.0  # 1 min candle replayed in 1 second

    # EMA Cross strategy defaults
    ema_fast_period: int = 3
    ema_slow_period: int = 7

    # RSI Mean Reversion strategy defaults
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70

    # Persistence
    state_file: str = "state.json"
    auto_save_interval_s: int = 30

    # Data source: "mock" or "zerodha"
    data_source: str = os.getenv("ALGOTRADEX_DATA_SOURCE", "mock")

    # Zerodha credentials (from env vars)
    zerodha_api_key: str = os.getenv("ALGOTRADEX_ZERODHA_API_KEY", "")
    zerodha_api_secret: str = os.getenv("ALGOTRADEX_ZERODHA_API_SECRET", "")

    # Token encryption key (Fernet)
    token_encryption_key: str = os.getenv("ALGOTRADEX_TOKEN_ENCRYPTION_KEY", "")

    # Risk
    max_position_pct: float = 0.20  # max 20% of capital in a single position
    max_order_value: float = 2_00_000.0  # ₹2 lakh per order
    max_open_positions: int = 5
    max_daily_loss_pct: float = 0.05  # 5% of initial capital

    # Bollinger Bands strategy defaults
    bb_period: int = 20
    bb_std_dev: float = 2.0


settings = Settings()
