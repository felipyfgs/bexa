"""Registro de estratégias por nome."""

from __future__ import annotations

from collections.abc import Callable

from bexa.core.exceptions import ConfigError
from bexa.strategy.base import Strategy
from bexa.strategy.candle_color import CandleColorStrategy
from bexa.strategy.hold import HoldStrategy

StrategyFactory = Callable[[], Strategy]

_REGISTRY: dict[str, StrategyFactory] = {
    "hold": HoldStrategy,
    "candle_color": CandleColorStrategy,
}


def register_strategy(name: str, factory: StrategyFactory) -> None:
    key = name.strip().lower()
    if not key:
        raise ConfigError("nome de estratégia vazio")
    _REGISTRY[key] = factory


def available_strategies() -> list[str]:
    return sorted(_REGISTRY)


def create_strategy(name: str) -> Strategy:
    key = (name or "hold").strip().lower()
    try:
        factory = _REGISTRY[key]
    except KeyError as exc:
        known = ", ".join(available_strategies())
        raise ConfigError(f"estratégia desconhecida: {name!r}. Disponíveis: {known}") from exc
    return factory()
