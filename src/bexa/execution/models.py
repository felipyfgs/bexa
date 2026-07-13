"""Modelos de intenção e resultado de execução no bexa."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ebinexpy import Direction, Order, Settlement, Timeframe

from bexa.execution.timing import OptionSchedule


@dataclass(frozen=True, slots=True)
class TradeIntent:
    """Intenção de trade OPTION (independente do wire do broker)."""

    symbol: str
    direction: Direction
    investment: Decimal
    timeframe: Timeframe
    price: Decimal | None = None
    wait_settlement: bool = True


@dataclass(frozen=True, slots=True)
class TradeResult:
    order: Order
    settlement: Settlement | None
    schedule: OptionSchedule | None = None
    wait_timeout_seconds: float | None = None
