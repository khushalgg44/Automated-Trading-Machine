"""Application configuration — all tunables in one place."""

from pydantic import BaseModel


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

    # Zerodha stub (placeholder for real OAuth later)
    kite_api_key: str = "mock_api_key"
    kite_access_token: str = "mock_access_token"

    # Data source: "mock" or "zerodha"
    data_source: str = "mock"

    # Zerodha credentials (from env vars)
    zerodha_api_key: str = ""
    zerodha_api_secret: str = ""

    # Risk
    max_position_pct: float = 0.20  # max 20% of capital in a single position
    max_order_value: float = 2_00_000.0  # ₹2 lakh per order
    max_open_positions: int = 5
    max_daily_loss_pct: float = 0.05  # 5% of initial capital

    # Bollinger Bands strategy defaults
    bb_period: int = 20
    bb_std_dev: float = 2.0


settings = Settings()
