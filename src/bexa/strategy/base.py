"""Contrato de estratégia pluggable."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bexa.strategy.models import BarContext, Signal


@runtime_checkable
class Strategy(Protocol):
    """Estratégia decide no fechamento da vela (entrada na seguinte)."""

    name: str

    async def on_bar_close(self, context: BarContext) -> Signal | None:
        """Retorna Signal para operar ou None para ficar de fora."""
        ...

    async def on_start(self) -> None:
        """Hook opcional no start do robô."""
        return None

    async def on_stop(self) -> None:
        """Hook opcional no stop do robô."""
        return None
