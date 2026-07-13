"""Testes unitários dos gates de execução (sem rede)."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from ebinexpy import AccountEnvironment, Direction, Timeframe

from bexa.config import Settings
from bexa.core.exceptions import ConfigError, ExecutionGuardError, RiskLimitError
from bexa.execution.guards import (
    as_money,
    assert_can_execute,
    require_demo_gate,
    require_real_cli_gate,
)
from bexa.execution.models import TradeIntent


def _settings(**kwargs: object) -> Settings:
    base = {
        "email": "a@b.com",
        "password": "x",
        "environment": AccountEnvironment.TEST,
        "allow_real_trading": False,
        "max_investment": Decimal("10"),
    }
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def _client(*, env: AccountEnvironment, allow_real: bool, connected: bool = True) -> MagicMock:
    client = MagicMock()
    client.connected = connected
    client.config.allow_real_trading = allow_real
    client.accounts.selected = SimpleNamespace(environment=env, id="acc-1")
    return client


def _intent(investment: str = "1") -> TradeIntent:
    return TradeIntent(
        symbol="IDXUSDT",
        direction=Direction.CALL,
        investment=Decimal(investment),
        timeframe=Timeframe.M1,
    )


def test_assert_can_execute_ok_test() -> None:
    client = _client(env=AccountEnvironment.TEST, allow_real=False)
    assert_can_execute(client, _settings(), _intent())


def test_blocks_when_disconnected() -> None:
    with pytest.raises(ExecutionGuardError, match="não está conectado"):
        assert_can_execute(
            _client(env=AccountEnvironment.TEST, allow_real=False, connected=False),
            _settings(),
            _intent(),
        )


def test_blocks_real_without_flag() -> None:
    # Settings REAL sem flag já falha na construção; aqui a conta selecionada
    # é REAL enquanto Settings permanece TEST (inconsistência / desvio de conta).
    with pytest.raises(ExecutionGuardError, match="REAL"):
        assert_can_execute(
            _client(env=AccountEnvironment.REAL, allow_real=False),
            _settings(environment=AccountEnvironment.TEST, allow_real_trading=False),
            _intent(),
        )


def test_allows_real_with_flags() -> None:
    settings = _settings(environment=AccountEnvironment.REAL, allow_real_trading=True)
    client = _client(env=AccountEnvironment.REAL, allow_real=True)
    assert_can_execute(client, settings, _intent())


def test_risk_limit() -> None:
    with pytest.raises(RiskLimitError):
        assert_can_execute(
            _client(env=AccountEnvironment.TEST, allow_real=False),
            _settings(max_investment=Decimal("5")),
            _intent("6"),
        )


def test_demo_gate() -> None:
    with pytest.raises(ExecutionGuardError):
        require_demo_gate(None)
    require_demo_gate("YES_ONE_DEMO_ORDER")


def test_real_cli_gate() -> None:
    with pytest.raises(ExecutionGuardError):
        require_real_cli_gate("YES")
    require_real_cli_gate("YES_ONE_REAL_ORDER")


def test_settings_real_requires_flag() -> None:
    with pytest.raises(ConfigError, match="YES_REAL_TRADING"):
        Settings(
            email="a@b.com",
            password="x",
            environment=AccountEnvironment.REAL,
            allow_real_trading=False,
        )


def test_as_money() -> None:
    assert as_money(Decimal("1.5")) == Decimal("1.5")
    assert as_money("2.0") == Decimal("2.0")
    assert as_money(3) == Decimal("3")
