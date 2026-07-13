"""Estratégia que nunca opera (padrão seguro)."""

from __future__ import annotations

from bexa.strategy.models import BarContext, Signal


class HoldStrategy:
    """Não gera sinais. Útil para smoke do loop sem ordens."""

    name = "hold"

    async def on_bar_close(self, context: BarContext) -> Signal | None:
        return None
