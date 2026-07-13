"""Config a partir do env: defaults, aliases e opt-ins estritos."""

from decimal import Decimal

import pytest
from ebinexpy import AccountEnvironment

from bexa.config import Settings
from bexa.core.exceptions import ConfigError


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBINEX_EMAIL", "a@b.com")
    monkeypatch.setenv("EBINEX_PASSWORD", "x")
    for key in (
        "BEXA_ENVIRONMENT",
        "BEXA_DEFAULT_SYMBOL",
        "BEXA_DEFAULT_TIMEFRAME",
        "BEXA_SYMBOL",
        "BEXA_TIMEFRAME",
        "BEXA_ALLOW_REAL_TRADING",
        "BEXA_BOT_STRATEGY",
        "BEXA_BOT_DRY_RUN",
        "BEXA_BOT_AUTO_TRADE",
        "BEXA_ALLOW_BOT",
        "BEXA_BOT_ENABLED",
        "BEXA_ALLOW_AUTO_REAL_TRADE",
    ):
        monkeypatch.delenv(key, raising=False)


def test_from_env_only_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    settings = Settings.from_env()
    assert settings.email == "a@b.com"
    assert settings.environment is AccountEnvironment.TEST
    assert settings.default_symbol == "IDXUSDT"
    assert settings.default_timeframe == "M1"
    assert settings.bot_dry_run is True
    assert settings.bot_auto_trade is False
    assert settings.bot_strategy == "hold"
    assert settings.bot_default_investment == Decimal("1")
    assert settings.settlement_timeout == 130.0
    assert settings.allow_real_trading is False
    assert settings.bot_allow_auto_real is False


def test_optional_overrides_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("BEXA_ENVIRONMENT", "TEST")
    monkeypatch.setenv("BEXA_SYMBOL", "BTCUSDT")
    monkeypatch.setenv("BEXA_TIMEFRAME", "M5")
    settings = Settings.from_env()
    assert settings.default_symbol == "BTCUSDT"
    assert settings.default_timeframe == "M5"


def test_default_symbol_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("BEXA_DEFAULT_SYMBOL", "ETHUSDT")
    monkeypatch.setenv("BEXA_SYMBOL", "BTCUSDT")
    settings = Settings.from_env()
    assert settings.default_symbol == "ETHUSDT"


def test_real_requires_exact_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("BEXA_ENVIRONMENT", "REAL")
    with pytest.raises(ConfigError, match="YES_REAL_TRADING"):
        Settings.from_env()

    # Valores genéricos NÃO habilitam REAL.
    for weak in ("1", "TRUE", "YES", "yes_real_trading"):
        monkeypatch.setenv("BEXA_ALLOW_REAL_TRADING", weak)
        with pytest.raises(ConfigError, match="YES_REAL_TRADING"):
            Settings.from_env()

    monkeypatch.setenv("BEXA_ALLOW_REAL_TRADING", "YES_REAL_TRADING")
    settings = Settings.from_env()
    assert settings.environment is AccountEnvironment.REAL
    assert settings.allow_real_trading is True


def test_auto_trade_exact_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("BEXA_BOT_AUTO_TRADE", "YES")
    assert Settings.from_env().bot_auto_trade is False

    monkeypatch.setenv("BEXA_BOT_AUTO_TRADE", "1")
    assert Settings.from_env().bot_auto_trade is False

    monkeypatch.setenv("BEXA_BOT_AUTO_TRADE", "YES_AUTO_TRADE")
    assert Settings.from_env().bot_auto_trade is True


def test_bot_enabled_needs_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("BEXA_BOT_ENABLED", "YES")
    assert Settings.from_env().bot_enabled is False

    monkeypatch.setenv("BEXA_ALLOW_BOT", "YES_RUN_BOT")
    assert Settings.from_env().bot_enabled is True


def test_auto_real_live_requires_extra_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("BEXA_ENVIRONMENT", "REAL")
    monkeypatch.setenv("BEXA_ALLOW_REAL_TRADING", "YES_REAL_TRADING")
    monkeypatch.setenv("BEXA_BOT_DRY_RUN", "0")
    monkeypatch.setenv("BEXA_BOT_AUTO_TRADE", "YES_AUTO_TRADE")
    with pytest.raises(ConfigError, match="YES_AUTO_REAL_TRADE"):
        Settings.from_env()

    monkeypatch.setenv("BEXA_ALLOW_AUTO_REAL_TRADE", "YES_AUTO_REAL_TRADE")
    settings = Settings.from_env()
    assert settings.bot_allow_auto_real is True
