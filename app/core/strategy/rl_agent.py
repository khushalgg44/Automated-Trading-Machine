"""Reinforcement Learning Trading Agent — Improved Version.

Improvements:
1. Better reward: penalizes inactivity, rewards trading
2. Supports more training data (Zerodha historical API)
3. Exposes agent confidence/thinking for UI display
4. Per-strategy portfolio isolation (tracks its own positions)
6. Training progress tracking via file
"""

import os
import math
import json
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Any

from app.event_bus import event_bus, Events
from app.core.strategy.base_strategy import BaseStrategy, Signal
from app.core.market.watchlist import watchlist


# ─── Trading Environment ───────────────────────────────────────────────────────

class TradingEnv(gym.Env):
    """Custom Gym environment with improved reward function."""

    metadata = {"render_modes": []}

    def __init__(self, prices: list[float], window_size: int = 20):
        super().__init__()
        self.prices = prices
        self.window_size = window_size
        self.action_space = spaces.Discrete(3)  # HOLD, BUY, SELL
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(window_size + 4,), dtype=np.float32
        )
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = self.window_size
        self.position = 0
        self.entry_price = 0.0
        self.total_reward = 0.0
        self.trades = 0
        self.hold_count = 0
        return self._get_obs(), {}

    def _get_obs(self) -> np.ndarray:
        window = self.prices[self.current_step - self.window_size:self.current_step]
        returns = [(window[i] - window[i-1]) / window[i-1] if window[i-1] != 0 else 0 for i in range(1, len(window))]
        while len(returns) < self.window_size:
            returns.insert(0, 0.0)

        rsi = self._compute_rsi() / 100.0
        ema_fast = self._ema(9)
        ema_slow = self._ema(21)
        ema_ratio = (ema_fast / ema_slow - 1.0) * 100 if ema_slow > 0 else 0.0
        pos_flag = float(self.position)
        current_price = self.prices[self.current_step - 1]
        unrealized = ((current_price - self.entry_price) / self.entry_price * 100) if self.position and self.entry_price > 0 else 0.0

        return np.array(returns + [rsi, ema_ratio, pos_flag, unrealized], dtype=np.float32)

    def step(self, action: int):
        current_price = self.prices[self.current_step - 1]
        reward = 0.0

        if action == 1 and self.position == 0:  # BUY
            self.position = 1
            self.entry_price = current_price
            self.hold_count = 0
            reward = 0.1  # Small reward for taking action (encourages trading)

        elif action == 2 and self.position == 1:  # SELL
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            reward = pnl_pct * 200  # Amplified reward for profitable trades
            if pnl_pct > 0:
                reward *= 1.5  # Extra bonus for profits
            self.position = 0
            self.entry_price = 0.0
            self.trades += 1
            self.hold_count = 0

        elif action == 0:  # HOLD
            self.hold_count += 1
            if self.position == 0:
                # Penalize holding flat for too long — force the agent to trade
                if self.hold_count > 10:
                    reward = -0.05 * (self.hold_count - 10)  # Increasing penalty
            else:
                # Holding a position: reward/penalize based on price movement
                if self.current_step > 1:
                    price_change = (current_price - self.prices[self.current_step - 2]) / self.prices[self.current_step - 2]
                    reward = price_change * 50  # Reward holding during uptrends

        self.current_step += 1
        self.total_reward += reward
        terminated = self.current_step >= len(self.prices)

        if terminated and self.position == 1:
            pnl_pct = (self.prices[-1] - self.entry_price) / self.entry_price
            reward += pnl_pct * 200
            self.position = 0
            self.trades += 1

        obs = self._get_obs() if not terminated else np.zeros(self.observation_space.shape, dtype=np.float32)
        return obs, reward, terminated, False, {}

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
        return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

    def _ema(self, period: int) -> float:
        if self.current_step < period:
            return self.prices[self.current_step - 1]
        prices = self.prices[self.current_step - period:self.current_step]
        k = 2.0 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema


# ─── Training with Progress ────────────────────────────────────────────────────

_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
_PROGRESS_FILE = os.path.join(_MODELS_DIR, "training_progress.json")


def _update_progress(symbol: str, current: int, total: int, status: str = "training"):
    """Write training progress to a file for the frontend to poll."""
    os.makedirs(_MODELS_DIR, exist_ok=True)
    progress = {
        "symbol": symbol,
        "current_step": current,
        "total_steps": total,
        "percent": round((current / total) * 100) if total > 0 else 0,
        "status": status,
    }
    with open(_PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def get_training_progress() -> dict | None:
    """Read current training progress."""
    if os.path.exists(_PROGRESS_FILE):
        try:
            with open(_PROGRESS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


class ProgressCallback:
    """Callback to track training progress."""
    def __init__(self, symbol: str, total_timesteps: int):
        self.symbol = symbol
        self.total = total_timesteps
        self.calls = 0
        _update_progress(symbol, 0, total_timesteps, "training")

    def __call__(self, locals_dict, globals_dict):
        self.calls += 1
        if self.calls % 10 == 0:  # Update every 10 calls
            try:
                num_timesteps = locals_dict.get("self").num_timesteps
                _update_progress(self.symbol, min(num_timesteps, self.total), self.total)
            except Exception:
                _update_progress(self.symbol, self.calls * 128, self.total)
        return True


def train_rl_agent(prices: list[float], symbol: str, timesteps: int = 20000) -> dict[str, Any]:
    """Train a PPO agent on historical price data with progress tracking."""
    from stable_baselines3 import PPO

    os.makedirs(_MODELS_DIR, exist_ok=True)
    _update_progress(symbol, 0, timesteps, "starting")

    env = TradingEnv(prices)

    model = PPO(
        "MlpPolicy", env, verbose=0,
        learning_rate=0.0003,
        n_steps=128,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        clip_range=0.2,
    )

    # Train with progress callback
    callback = ProgressCallback(symbol, timesteps)
    model.learn(total_timesteps=timesteps, callback=callback)

    # Save model
    model_path = os.path.join(_MODELS_DIR, f"rl_{symbol.lower()}")
    model.save(model_path)
    _update_progress(symbol, timesteps, timesteps, "evaluating")

    # Evaluate
    eval_env = TradingEnv(prices)
    obs, _ = eval_env.reset()
    total_reward = 0
    actions_taken = {"BUY": 0, "SELL": 0, "HOLD": 0}
    equity_curve = [1.0]
    capital = 1.0

    while True:
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        if action == 0: actions_taken["HOLD"] += 1
        elif action == 1: actions_taken["BUY"] += 1
        elif action == 2: actions_taken["SELL"] += 1

        obs, reward, terminated, truncated, _ = eval_env.step(action)
        total_reward += reward
        capital += reward / 100
        equity_curve.append(capital)
        if terminated or truncated:
            break

    _update_progress(symbol, timesteps, timesteps, "complete")

    return {
        "symbol": symbol,
        "model_path": model_path,
        "timesteps": timesteps,
        "total_reward": round(total_reward, 2),
        "trades": eval_env.trades,
        "final_return_pct": round((capital - 1.0) * 100, 2),
        "actions": actions_taken,
        "equity_curve": equity_curve[::max(1, len(equity_curve) // 100)],
    }


def load_rl_model(symbol: str):
    """Load a trained model for a symbol."""
    from stable_baselines3 import PPO
    model_path = os.path.join(_MODELS_DIR, f"rl_{symbol.lower()}")
    if os.path.exists(model_path + ".zip"):
        return PPO.load(model_path)
    return None


# ─── Live Strategy with Isolated Portfolio + Confidence Display ────────────────

class RLAgentStrategy(BaseStrategy):
    """RL agent with its own isolated position tracking and confidence reporting."""

    name = "rl_agent"

    def __init__(self, symbol: str = "RELIANCE", qty: int = 5) -> None:
        super().__init__()
        self.symbol = symbol
        self.qty = qty
        self._model = None
        self._prices: list[float] = []
        self._own_position = 0  # Isolated: only tracks RL agent's own position
        self._own_entry_price = 0.0
        self._window_size = 20
        self._last_confidence: dict[str, float] = {}  # action -> probability

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

        if len(self._prices) > 200:
            self._prices = self._prices[-200:]

        obs = self._build_obs(price)

        # Get action AND probabilities (confidence)
        action, _ = self._model.predict(obs, deterministic=True)
        action = int(action)

        # Get action probabilities for confidence display
        try:
            obs_tensor = self._model.policy.obs_to_tensor(obs.reshape(1, -1))[0]
            dist = self._model.policy.get_distribution(obs_tensor)
            probs = dist.distribution.probs.detach().numpy()[0]
            self._last_confidence = {
                "HOLD": round(float(probs[0]) * 100, 1),
                "BUY": round(float(probs[1]) * 100, 1),
                "SELL": round(float(probs[2]) * 100, 1),
            }
        except Exception:
            self._last_confidence = {}

        # Isolated position tracking
        if action == 1 and self._own_position == 0:  # BUY
            self._own_position = 1
            self._own_entry_price = price
            confidence = self._last_confidence.get("BUY", 0)
            return Signal(
                direction=Signal.BUY,
                symbol=self.symbol,
                quantity=self.qty,
                reason=f"RL Agent BUY (confidence: {confidence}%)",
            )
        elif action == 2 and self._own_position == 1:  # SELL
            pnl_pct = ((price - self._own_entry_price) / self._own_entry_price * 100) if self._own_entry_price > 0 else 0
            self._own_position = 0
            self._own_entry_price = 0.0
            confidence = self._last_confidence.get("SELL", 0)
            return Signal(
                direction=Signal.SELL,
                symbol=self.symbol,
                quantity=self.qty,
                reason=f"RL Agent SELL (confidence: {confidence}%, P&L: {pnl_pct:+.2f}%)",
            )

        return None

    def get_confidence(self) -> dict[str, Any]:
        """Return current agent state for UI display."""
        return {
            "symbol": self.symbol,
            "position": "LONG" if self._own_position == 1 else "FLAT",
            "entry_price": self._own_entry_price,
            "confidence": self._last_confidence,
        }

    def _build_obs(self, current_price: float) -> np.ndarray:
        prices = self._prices
        n = len(prices)
        window = prices[n - self._window_size:n]

        returns = [(window[i] - window[i-1]) / window[i-1] if window[i-1] != 0 else 0 for i in range(1, len(window))]
        while len(returns) < self._window_size:
            returns.insert(0, 0.0)

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

        ema_fast = self._ema(prices, 9)
        ema_slow = self._ema(prices, 21)
        ema_ratio = (ema_fast / ema_slow - 1.0) * 100 if ema_slow > 0 else 0.0

        pos_flag = float(self._own_position)
        unrealized = ((current_price - self._own_entry_price) / self._own_entry_price * 100) if self._own_position and self._own_entry_price > 0 else 0.0

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
