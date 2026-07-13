"""Testes de estratégia, risco e registro."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from ebinexpy import Candle, Direction, Timeframe

from bexa.config import Settings
from bexa.core.exceptions import ConfigError
from bexa.risk import RiskService
from bexa.strategy import available_strategies, create_strategy
from bexa.strategy.models import BarContext, Signal


def _settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {
        "email": "a@b.com",
        "password": "x",
        "max_investment": Decimal("10"),
        "bot_default_investment": Decimal("1"),
        "bot_max_trades": 3,
        "bot_max_open_orders": 1,
        "bot_cooldown_seconds": 0,
        "bot_max_daily_loss": Decimal("5"),
    }
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def _candle(o: str, c: str) -> Candle:
    return Candle(
        symbol="IDXUSDT",
        timeframe=Timeframe.M1,
        open_time=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        open=Decimal(o),
        high=Decimal("10"),
        low=Decimal("1"),
        close=Decimal(c),
        volume=Decimal("1"),
    )


@pytest.mark.asyncio
async def test_hold_never_signals() -> None:
    strategy = create_strategy("hold")
    ctx = BarContext(
        symbol="IDXUSDT",
        timeframe=Timeframe.M1,
        closed=_candle("5", "6"),
    )
    assert await strategy.on_bar_close(ctx) is None


@pytest.mark.asyncio
async def test_candle_color_call_put() -> None:
    strategy = create_strategy("candle_color")
    up = await strategy.on_bar_close(BarContext("IDXUSDT", Timeframe.M1, _candle("5", "6")))
    down = await strategy.on_bar_close(BarContext("IDXUSDT", Timeframe.M1, _candle("6", "5")))
    flat = await strategy.on_bar_close(BarContext("IDXUSDT", Timeframe.M1, _candle("5", "5")))
    assert up is not None and up.direction is Direction.CALL
    assert down is not None and down.direction is Direction.PUT
    assert flat is None


def test_unknown_strategy() -> None:
    with pytest.raises(ConfigError):
        create_strategy("nao-existe")
    assert "hold" in available_strategies()


def test_risk_blocks_max_open_and_loss() -> None:
    risk = RiskService(_settings())
    signal = Signal(direction=Direction.CALL)
    assert risk.evaluate_signal(signal, Decimal("1")).allowed

    risk.on_order_submitted()
    blocked = risk.evaluate_signal(signal, Decimal("1"))
    assert not blocked.allowed
    assert "abertas" in blocked.reason

    risk.on_order_settled(Decimal("-3"))
    risk.on_order_submitted()
    risk.on_order_settled(Decimal("-3"))
    stopped = risk.evaluate_signal(signal, Decimal("1"))
    assert not stopped.allowed
    assert "perda" in stopped.reason.lower() or risk.state.stopped_reason


def test_risk_blocks_stake_above_max() -> None:
    risk = RiskService(_settings(max_investment=Decimal("5")))
    decision = risk.evaluate_signal(Signal(direction=Direction.CALL), Decimal("6"))
    assert not decision.allowed
    assert "max" in decision.reason


def test_history_lookback_scales_with_timeframe() -> None:
    from bexa.market.service import history_lookback_minutes

    m1 = history_lookback_minutes(Timeframe.M1, 50)
    m5 = history_lookback_minutes(Timeframe.M5, 50)
    m15 = history_lookback_minutes(Timeframe.M15, 50)
    assert m1 >= 50
    assert m5 > m1
    assert m15 > m5
    # 50 velas M5 ≈ 250 min + margem
    assert m5 >= 250
