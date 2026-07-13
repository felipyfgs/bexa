"""Controles de risco para o robô automático."""

from __future__ import annotations

import time
from decimal import Decimal

from bexa.config import Settings
from bexa.core.exceptions import RiskLimitError
from bexa.core.logging import get_logger
from bexa.risk.models import RiskDecision, RiskState
from bexa.strategy.models import Signal

log = get_logger("bexa.risk")


class RiskService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.state = RiskState()

    def evaluate_signal(self, signal: Signal, investment: Decimal) -> RiskDecision:
        st = self.state
        if st.stopped_reason:
            return RiskDecision(False, st.stopped_reason)

        if investment <= 0:
            return RiskDecision(False, "investment deve ser positivo")
        if investment > self._settings.max_investment:
            return RiskDecision(
                False,
                f"investment {investment} > max {self._settings.max_investment}",
            )

        if st.open_orders >= self._settings.bot_max_open_orders:
            return RiskDecision(
                False,
                f"max ordens abertas ({self._settings.bot_max_open_orders}) atingido",
            )

        if st.trades_opened >= self._settings.bot_max_trades:
            return RiskDecision(
                False,
                f"max trades da sessão ({self._settings.bot_max_trades}) atingido",
            )

        if self._settings.bot_cooldown_seconds > 0 and st.last_order_at is not None:
            elapsed = time.monotonic() - st.last_order_at
            if elapsed < self._settings.bot_cooldown_seconds:
                remain = self._settings.bot_cooldown_seconds - elapsed
                return RiskDecision(False, f"cooldown ({remain:.0f}s restantes)")

        max_loss = self._settings.bot_max_daily_loss
        if max_loss > 0 and st.realized_pnl <= -max_loss:
            st.stopped_reason = f"stop por perda ({st.realized_pnl} <= -{max_loss})"
            return RiskDecision(False, st.stopped_reason)

        return RiskDecision(True, "ok")

    def require_signal(self, signal: Signal, investment: Decimal) -> None:
        decision = self.evaluate_signal(signal, investment)
        if not decision.allowed:
            raise RiskLimitError(decision.reason)

    def on_order_submitted(self) -> None:
        self.state.trades_opened += 1
        self.state.open_orders += 1
        self.state.last_order_at = time.monotonic()
        self.state.last_signal_at = self.state.last_order_at
        log.info(
            "risco: ordem aberta trades=%s open=%s",
            self.state.trades_opened,
            self.state.open_orders,
        )

    def on_order_settled(self, profit: Decimal) -> None:
        self.state.open_orders = max(0, self.state.open_orders - 1)
        self.state.trades_settled += 1
        self.state.realized_pnl += profit
        log.info(
            "risco: settlement profit=%s pnl=%s open=%s settled=%s",
            profit,
            self.state.realized_pnl,
            self.state.open_orders,
            self.state.trades_settled,
        )
        max_loss = self._settings.bot_max_daily_loss
        if max_loss > 0 and self.state.realized_pnl <= -max_loss:
            self.state.stopped_reason = (
                f"stop por perda ({self.state.realized_pnl} <= -{max_loss})"
            )
            log.warning("risco: %s", self.state.stopped_reason)

    def should_stop(self) -> bool:
        if self.state.stopped_reason:
            return True
        max_trades = self._settings.bot_max_trades
        if self.state.trades_opened >= max_trades and self.state.open_orders == 0:
            self.state.stopped_reason = "max trades da sessão concluído"
            return True
        return False
