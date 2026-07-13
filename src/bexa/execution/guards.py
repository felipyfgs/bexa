"""Gates de segurança antes de enviar ordem à Ebinex."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ebinexpy import AccountEnvironment, EbinexClient

from bexa.config import Settings
from bexa.core.exceptions import ExecutionGuardError, RiskLimitError
from bexa.execution.models import TradeIntent
from bexa.execution.timing import entry_window


def assert_can_execute(client: EbinexClient, settings: Settings, intent: TradeIntent) -> None:
    """Bloqueia envio se ambiente/risco/config/janela de entrada inconsistentes."""
    if not client.connected:
        raise ExecutionGuardError("Cliente não está conectado")

    selected = client.accounts.selected
    if selected is None:
        raise ExecutionGuardError("Nenhuma conta selecionada")

    if selected.environment is AccountEnvironment.REAL:
        if not settings.allow_real_trading:
            raise ExecutionGuardError(
                "Conta REAL selecionada sem BEXA_ALLOW_REAL_TRADING (opt-in)"
            )
        if not client.config.allow_real_trading:
            raise ExecutionGuardError(
                "ClientConfig.allow_real_trading=False; ebinexpy bloquearia a ordem REAL"
            )
        if settings.environment is not AccountEnvironment.REAL:
            raise ExecutionGuardError(
                "Conta REAL ativa, mas Settings.environment não é REAL — recuse por inconsistência"
            )

    if intent.investment <= 0:
        raise RiskLimitError("investment deve ser positivo")

    if intent.investment > settings.max_investment:
        raise RiskLimitError(
            f"investment {intent.investment} excede max_investment={settings.max_investment}"
        )

    if not intent.symbol.strip():
        raise ExecutionGuardError("symbol é obrigatório")

    if intent.price is not None and intent.price <= 0:
        raise ExecutionGuardError("price deve ser positivo quando informado")

    # Corte de entrada da UI Ebinex (M1: a partir do s:55 CALL/PUT somem).
    broker = client.get_broker_time()
    clock = broker.value if broker is not None else datetime.now(UTC)
    window = entry_window(intent.timeframe, now=clock)
    if not window.open:
        raise ExecutionGuardError(window.reason)


def require_demo_gate(env_flag: str | None, expected: str = "YES_ONE_DEMO_ORDER") -> None:
    """Gate explícito para ordens de demo via CLI (evita clique acidental)."""
    if (env_flag or "").strip() != expected:
        raise ExecutionGuardError(
            f"Defina BEXA_ALLOW_DEMO_ORDER={expected} de propósito para enviar ordem DEMO/TEST"
        )


def require_real_cli_gate(env_flag: str | None, expected: str = "YES_ONE_REAL_ORDER") -> None:
    """Gate extra só na CLI de ordem REAL (além de BEXA_ALLOW_REAL_TRADING)."""
    if (env_flag or "").strip() != expected:
        raise ExecutionGuardError(
            f"Defina BEXA_ALLOW_REAL_ORDER={expected} de propósito para enviar UMA ordem REAL"
        )


def as_money(value: Decimal | str | int | float) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))
