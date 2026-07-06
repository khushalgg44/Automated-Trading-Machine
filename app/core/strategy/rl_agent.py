"""Reinforcement Learning Trading Agent.

Uses a PPO (Proximal Policy Optimization) agent trained on historical price data.
The agent learns when to BUY, SELL, or HOLD based on market state features.
"""

import os
import math
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Any

from app.event_bus import event_bus, Events
from app.core.strategy.base_strategy import BaseStrategy, Signal
from app.core.market.watchlist import watchlist


# ─── Trading Environment for Training ─────────────────────────────────────────

class TradingEnv(gym.Env):
    """Custom Gym environment for training the RL agent on historical data."""

    metadata = {"render_modes": []}

    def __init__(self, prices: list[float], window_size: int = 20):
        super().__init__()
        self.prices = prices
        self.window_size = window_size

        # Actions: 0=HOLD, 1=BUY, 2=SELL
        self.action_space = spaces.Discrete(3)

        # Observation: window of normalized price changes + RSI + position flag
        # Features: window_size price returns + RSI + EMA ratio + position (0/1) + unrealized_pnl
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(window_size + 4,), dtype=np.float32
        )

        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = self.window_size
        self.position = 0  # 0=flat, 1=long
        self.entry_price = 0.0
        self.total_reward = 0.0
        self.trades = 0
        return self._get_obs(), {}

    def _get_obs(self) -> np.ndarray:
        # Price returns (normalized)
        window = self.prices[self.current_step - self.window_size:self.current_step]
        returns = [(window[i] - window[i-1]) / window[i-1] for i in range(1, len(window))]
        # Pad to window_size
        while len(returns) < self.window_size:
            returns.insert(0, 0.0)

        # RSI (14 period)
        rsi = self._compute_rsi() / 100.0  # normalize to 0-1

        # EMA ratio
        ema_fast = self._ema(9)
        ema_slow = self._ema(21)
        ema_ratio = (ema_fast / ema_slow - 1.0) * 100 if ema_slow > 0 else 0.0

        # Position flag
        pos_flag = float(self.position)

        # Unrealized PnL (normalized)
        current_price = self.prices[self.current_step - 1]
        unrealized = ((current_price - self.entry_price) / self.entry_price * 100) if self.position and self.entry_price > 0 else 0.0

        obs = np.array(returns + [rsi, ema_ratio, pos_flag, unrealized], dtype=np.float32)
        return obs

    def step(self, action: int):
        current_price = self.prices[self.current_step - 1]
        reward = 0.0
        terminated = False

        if action == 1 and self.position == 0:  # BUY
            self.position = 1
            self.entry_price = current_price
            reward = -0.001  # small cost for trading

        elif action == 2 and self.position == 1:  # SELL
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            reward = pnl_pct * 100  # reward proportional to profit %
            self.position = 0
            self.entry_price = 0.0
            self.trades += 1

        elif action == 0:  # HOLD
            if self.position == 1:
                # Small reward/penalty for holding based on price movement
                if self.current_step < len(self.prices):
                    next_ret = (current_price - self.prices[self.current_step - 2]) / self.prices[self.current_step - 2]
                    reward = next_ret * 10  # incentivize holding during uptrends

        self.current_step += 1
        self.total_reward += reward

        if self.current_step >= len(self.prices):
            terminated = True
            # Force close any open position
            if self.position == 1:
                pnl_pct = (self.prices[-1] - self.entry_price) / self.entry_price
                reward += pnl_pct * 100
                self.position = 0

        truncated = False
        return self._get_obs() if not terminated else np.zeros(self.observation_space.shape, dtype=np.float32), reward, terminated, truncated, {}

    def _compute_rsi(self, period: int = 14) -> float:
        if self.current_step < period + 1:
            return 50.0
        prices = self.prices[self.current_step - period - 1:self.current_step]
        gains = [max(0, prices[i] - prices[i-1]) for i in range(1, len(prices))]
        losses = [max(0, prices[i-1] - prices[i]) for i in range(1, len(prices))]
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _ema(self, period: int) -> float:
        if self.current_step < period:
            return self.prices[self.current_step - 1]
        prices = self.prices[self.current_step - period:self.current_step]
        k = 2.0 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema


# ─── Training Function ─────────────────────────────────────────────────────────

_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")


def train_rl_agent(prices: list[float], symbol: str, timesteps: int = 20000) -> dict[str, Any]:
    """Train a PPO agent on historical price data.

    Args:
        prices: list of closing prices
        symbol: stock symbol (for model filename)
        timesteps: training steps (more = better but slower)

    Returns:
        Training result stats
    """
    from stable_baselines3 import PPO

    os.makedirs(_MODELS_DIR, exist_ok=True)

    env = TradingEnv(prices)
    model = PPO("MlpPolicy", env, verbose=0, learning_rate=0.0003, n_steps=256, batch_size=64)
    model.learn(total_timesteps=timesteps)

    # Save model
    model_path = os.path.join(_MODELS_DIR, f"rl_{symbol.lower()}")
    model.save(model_path)

    # Evaluate: run one episode and track results
    eval_env = TradingEnv(prices)
    obs, _ = eval_env.reset()
    total_reward = 0
    trades = 0
    equity_curve = [1.0]  # normalized
    capital = 1.0

    while True:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, _ = eval_env.step(int(action))
        total_reward += reward
        capital += reward / 100
        equity_curve.append(capital)
        if terminated or truncated:
            trades = eval_env.trades
            break

    return {
        "symbol": symbol,
        "model_path": model_path,
        "timesteps": timesteps,
        "total_reward": round(total_reward, 2),
        "trades": trades,
        "final_return_pct": round((capital - 1.0) * 100, 2),
        "equity_curve": equity_curve[::max(1, len(equity_curve) // 100)],  # downsample to 100 points
    }


def load_rl_model(symbol: str):
    """Load a trained model for a symbol."""
    from stable_baselines3 import PPO
    model_path = os.path.join(_MODELS_DIR, f"rl_{symbol.lower()}")
    if os.path.exists(model_path + ".zip"):
        return PPO.load(model_path)
    return None


# ─── Live Strategy ─────────────────────────────────────────────────────────────

class RLAgentStrategy(BaseStrategy):
    """Reinforcement Learning agent running as a live strategy."""

    name = "rl_agent"

    def __init__(self, symbol: str = "RELIANCE", qty: int = 5) -> None:
        super().__init__()
        self.symbol = symbol
        self.qty = qty
        self._model = None
        self._prices: list[float] = []
        self._position = 0  # 0=flat, 1=long
        self._window_size = 20

    async def _on_start(self) -> None:
        self._model = load_rl_model(self.symbol)
        if not self._model:
            print(f"[RL Agent] No trained model found for {self.symbol}. Train first.")
            return
        event_bus.subscribe(Events.TICK_RECEIVED, self._handle_tick)
        print(f"[RL Agent] Loaded model for {self.symbol}. Active.")

    async def _on_stop(self) -> None:
        event_bus.unsubscribe(Events.TICK_RECEIVED, self._handle_tick)

    async def _handle_tick(self, payload: dict[str, Any]) -> None:
        if payload["symbol"] != self.symbol:
            return
        if not watchlist.contains(payload["symbol"]):
            return
        signal = await self.on_tick(payload)
        if signal:
            await event_bus.publish(
                Events.SIGNAL_GENERATED,
                {"signal": signal, "strategy": self.name},
            )

    async def on_tick(self, payload: dict[str, Any]) -> Signal | None:
        if not self._active or not self._model:
            return None

        price = payload["ltp"]
        self._prices.append(price)

        if len(self._prices) < self._window_size + 5:
            return None

        # Keep sliding window
        if len(self._prices) > 200:
            self._prices = self._prices[-200:]

        # Build observation
        obs = self._build_obs()
        action, _ = self._model.predict(obs, deterministic=True)

        if action == 1 and self._position == 0:  # BUY
            self._position = 1
            return Signal(
                direction=Signal.BUY,
                symbol=self.symbol,
                quantity=self.qty,
                reason="RL Agent: BUY signal (learned pattern detected)",
            )
        elif action == 2 and self._position == 1:  # SELL
            self._position = 0
            return Signal(
                direction=Signal.SELL,
                symbol=self.symbol,
                quantity=self.qty,
                reason="RL Agent: SELL signal (exit pattern detected)",
            )

        return None

    def _build_obs(self) -> np.ndarray:
        prices = self._prices
        n = len(prices)
        window = prices[n - self._window_size:n]

        # Returns
        returns = [(window[i] - window[i-1]) / window[i-1] for i in range(1, len(window))]
        while len(returns) < self._window_size:
            returns.insert(0, 0.0)

        # RSI
        rsi = 50.0
        if n >= 15:
            gains = [max(0, prices[n-14+i] - prices[n-15+i]) for i in range(14)]
            losses = [max(0, prices[n-15+i] - prices[n-14+i]) for i in range(14)]
            ag = sum(gains) / 14
            al = sum(losses) / 14
            if al > 0:
                rsi = 100.0 - (100.0 / (1.0 + ag / al))
            else:
                rsi = 100.0

        # EMA ratio
        ema_fast = self._ema(prices, 9)
        ema_slow = self._ema(prices, 21)
        ema_ratio = (ema_fast / ema_slow - 1.0) * 100 if ema_slow > 0 else 0.0

        pos_flag = float(self._position)
        unrealized = 0.0

        return np.array(returns + [rsi / 100.0, ema_ratio, pos_flag, unrealized], dtype=np.float32)

    def _ema(self, prices: list[float], period: int) -> float:
        if len(prices) < period:
            return prices[-1]
        window = prices[-period:]
        k = 2.0 / (period + 1)
        ema = window[0]
        for p in window[1:]:
            ema = p * k + ema * (1 - k)
        return ema
