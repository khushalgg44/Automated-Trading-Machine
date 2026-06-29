"""Strategy registry — manages lifecycle of all registered strategies."""

from app.core.strategy.base_strategy import BaseStrategy
from app.core.strategy.ema_cross import EMACrossStrategy
from app.core.strategy.rsi_mean_reversion import RSIMeanReversionStrategy
from app.core.strategy.bollinger_bands import BollingerBandsStrategy


class StrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, BaseStrategy] = {}

    def register(self, strategy: BaseStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> BaseStrategy | None:
        return self._strategies.get(name)

    def list_all(self) -> list[str]:
        return list(self._strategies.keys())

    async def start(self, name: str) -> bool:
        strategy = self._strategies.get(name)
        if not strategy:
            return False
        await strategy.start()
        return True

    async def stop(self, name: str) -> bool:
        strategy = self._strategies.get(name)
        if not strategy:
            return False
        await strategy.stop()
        return True

    async def stop_all(self) -> None:
        for strategy in self._strategies.values():
            if strategy.is_active:
                await strategy.stop()


# Singleton with all strategies pre-registered (bollinger not auto-started)
strategy_registry = StrategyRegistry()
strategy_registry.register(EMACrossStrategy())
strategy_registry.register(RSIMeanReversionStrategy())
strategy_registry.register(BollingerBandsStrategy())
