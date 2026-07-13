"""Testes do modelo de tempo OPTION (vela seguinte)."""

from datetime import UTC, datetime
from decimal import Decimal

from ebinexpy import Direction, Order, OrderRequest, OrderStatus, Timeframe

from bexa.execution.timing import (
    entry_window,
    expected_schedule,
    next_candle_open,
    schedule_from_order,
    settlement_wait_seconds,
    timeframe_duration_seconds,
)


def test_m1_next_open_aligns_to_minute() -> None:
    now = datetime(2026, 7, 13, 12, 0, 25, tzinfo=UTC)
    open_at = next_candle_open(now, Timeframe.M1)
    assert open_at == datetime(2026, 7, 13, 12, 1, 0, tzinfo=UTC)


def test_expected_schedule_is_next_candle_then_full_duration() -> None:
    # 25s dentro do minuto → 35s até abrir + 60s de vela = 95s até liquidar
    now = datetime(2026, 7, 13, 12, 0, 25, tzinfo=UTC)
    schedule = expected_schedule(Timeframe.M1, now=now)
    assert schedule.open_at == datetime(2026, 7, 13, 12, 1, 0, tzinfo=UTC)
    assert schedule.settle_at == datetime(2026, 7, 13, 12, 2, 0, tzinfo=UTC)
    assert schedule.seconds_until_open == 35.0
    assert schedule.seconds_until_settle == 95.0
    assert schedule.wait_timeout(buffer_seconds=20) == 115.0


def test_worst_case_m1_just_after_open() -> None:
    # 1s após o início → quase 2 minutos até liquidar
    now = datetime(2026, 7, 13, 12, 0, 1, tzinfo=UTC)
    schedule = expected_schedule(Timeframe.M1, now=now)
    assert schedule.seconds_until_settle == 119.0
    assert settlement_wait_seconds(Timeframe.M1, now=now, buffer_seconds=20) == 139.0


def test_m5_duration() -> None:
    assert timeframe_duration_seconds(Timeframe.M5) == 300.0
    now = datetime(2026, 7, 13, 12, 1, 0, tzinfo=UTC)
    schedule = expected_schedule(Timeframe.M5, now=now)
    # próximo open M5 em 12:05; settle 12:10
    assert schedule.open_at == datetime(2026, 7, 13, 12, 5, 0, tzinfo=UTC)
    assert schedule.settle_at == datetime(2026, 7, 13, 12, 10, 0, tzinfo=UTC)


def test_m1_entry_window_open_before_55() -> None:
    # 12:00:40 → ainda pode enviar (corte em :55)
    now = datetime(2026, 7, 13, 12, 0, 40, tzinfo=UTC)
    window = entry_window(Timeframe.M1, now=now)
    assert window.open is True
    assert window.elapsed_seconds == 40.0
    assert window.cutoff_seconds == 55.0
    assert abs(window.remaining_until_cutoff - 15.0) < 1e-6


def test_m1_entry_window_closed_from_55() -> None:
    # A partir do segundo 55 os botões CALL/PUT somem na Ebinex
    now = datetime(2026, 7, 13, 12, 0, 55, tzinfo=UTC)
    window = entry_window(Timeframe.M1, now=now)
    assert window.open is False
    assert window.elapsed_seconds == 55.0

    late = datetime(2026, 7, 13, 12, 0, 59, tzinfo=UTC)
    assert entry_window(Timeframe.M1, now=late).open is False


def test_m5_entry_window_locks_last_5s() -> None:
    # M5 = 300s; corte em 295s (mesma cauda de 5s)
    now = datetime(2026, 7, 13, 12, 4, 56, tzinfo=UTC)  # 4*60+56 = 296s na vela
    window = entry_window(Timeframe.M5, now=now)
    assert window.cutoff_seconds == 295.0
    assert window.open is False


def test_schedule_from_order_prefers_broker_fields() -> None:
    open_at = datetime(2026, 7, 13, 12, 1, 0, tzinfo=UTC)
    settle_at = datetime(2026, 7, 13, 12, 2, 0, tzinfo=UTC)
    order = Order(
        id="abc",
        request=OrderRequest(
            symbol="IDXUSDT",
            direction=Direction.CALL,
            investment=Decimal("1"),
            timeframe=Timeframe.M1,
        ),
        status=OrderStatus.PENDING,
        placed_at=datetime(2026, 7, 13, 12, 0, 30, tzinfo=UTC),
        scheduled_open_at=open_at,
        expires_at=settle_at,
    )
    now = datetime(2026, 7, 13, 12, 0, 30, tzinfo=UTC)
    schedule = schedule_from_order(order, now=now)
    assert schedule.open_at == open_at
    assert schedule.settle_at == settle_at
    assert settlement_wait_seconds(
        Timeframe.M1, order=order, now=now, buffer_seconds=10, floor_seconds=0
    ) == 100.0
