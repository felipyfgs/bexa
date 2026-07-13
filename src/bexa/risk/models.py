"""Estado e decisões de risco do robô."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class RiskState:
    trades_opened: int = 0
    trades_settled: int = 0
    open_orders: int = 0
    realized_pnl: Decimal = Decimal("0")
    last_signal_at: float | None = None
    last_order_at: float | None = None
    stopped_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RiskDecision:
    allowed: bool
    reason: str = ""
