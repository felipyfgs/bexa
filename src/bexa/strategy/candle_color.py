"""Estratégia simples: vela de alta → CALL, vela de baixa → PUT.

Somente para validar o pipeline automático em TEST. Não é edge real.
"""

from __future__ import annotations

from ebinexpy import Direction

from bexa.strategy.models import BarContext, Signal


class CandleColorStrategy:
    name = "candle_color"

    async def on_bar_close(self, context: BarContext) -> Signal | None:
        candle = context.closed
        if candle.close > candle.open:
            direction = Direction.CALL
            reason = "vela de alta (close > open)"
        elif candle.close < candle.open:
            direction = Direction.PUT
            reason = "vela de baixa (close < open)"
        else:
            return None
        return Signal(
            direction=direction,
            symbol=context.symbol,
            timeframe=context.timeframe,
            reason=reason,
        )
