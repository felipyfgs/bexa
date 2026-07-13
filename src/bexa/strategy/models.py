"""Modelos de sinal e contexto de barra para estratégias."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ebinexpy import Candle, Direction, Timeframe


@dataclass(frozen=True, slots=True)
class BarContext:
    """Contexto passado à estratégia ao fechar uma vela."""

    symbol: str
    timeframe: Timeframe
    closed: Candle
    history: tuple[Candle, ...] = ()
    broker_time: datetime | None = None
    balance: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Signal:
    """Sinal de entrada. O robô envia agora; execução entra na vela seguinte."""

    direction: Direction
    symbol: str | None = None
    timeframe: Timeframe | None = None
    investment: Decimal | None = None
    reason: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
