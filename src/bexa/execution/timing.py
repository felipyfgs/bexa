"""Modelo de tempo das OPTION na Ebinex.

Fluxo típico:
1. Envio agora (ainda dentro da vela N) — **só enquanto a janela de entrada
   estiver aberta** (na UI, botões CALL/PUT somem a partir do segundo 55 no M1).
2. Abertura / execução na **vela seguinte** (N+1).
3. Liquidação no **fim da vela seguinte** (fim de N+1).

Portanto o pior caso de espera, a partir de "agora", é:
  resto da vela atual + duração completa da vela seguinte
  ≈ até 2 × timeframe (+ margem de rede/evento).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ebinexpy import Order, Timeframe

# Durações oficiais alinhadas ao ebinexpy (ms).
_TIMEFRAME_MS: dict[Timeframe, int] = {
    Timeframe.M1: 60_000,
    Timeframe.M5: 300_000,
    Timeframe.M15: 900_000,
}

# Margem extra para latência, reconciliação REST e atraso de evento WS.
DEFAULT_BUFFER_SECONDS = 20.0

# Na Ebinex (M1), a partir do segundo 55 da vela corrente os botões CALL/PUT
# somem — não dá mais para agendar a entrada na vela seguinte.
# Para M5/M15 usamos a mesma trava de 5s no final da vela (duração - 5).
M1_ENTRY_CUTOFF_ELAPSED_SECONDS = 55.0
ENTRY_LOCKOUT_TAIL_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class OptionSchedule:
    """Janela esperada da ordem OPTION."""

    now: datetime
    timeframe: Timeframe
    # Início da vela de execução (vela seguinte).
    open_at: datetime
    # Fim da vela de execução / liquidação esperada.
    settle_at: datetime
    candle_seconds: float

    @property
    def seconds_until_open(self) -> float:
        return max(0.0, (self.open_at - self.now).total_seconds())

    @property
    def seconds_until_settle(self) -> float:
        return max(0.0, (self.settle_at - self.now).total_seconds())

    def wait_timeout(self, buffer_seconds: float = DEFAULT_BUFFER_SECONDS) -> float:
        """Timeout recomendado para wait_order (settle + margem)."""
        return self.seconds_until_settle + max(0.0, buffer_seconds)


def timeframe_duration_ms(timeframe: Timeframe) -> int:
    try:
        return _TIMEFRAME_MS[timeframe]
    except KeyError as exc:
        raise ValueError(f"timeframe sem duração mapeada: {timeframe}") from exc


def timeframe_duration_seconds(timeframe: Timeframe) -> float:
    return timeframe_duration_ms(timeframe) / 1000.0


def next_candle_open(now: datetime, timeframe: Timeframe) -> datetime:
    """Início da vela seguinte (momento em que a ordem entra em execução)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    duration_ms = timeframe_duration_ms(timeframe)
    now_ms = int(now.timestamp() * 1000)
    open_ms = ((now_ms // duration_ms) + 1) * duration_ms
    return datetime.fromtimestamp(open_ms / 1000, tz=UTC)


def candle_elapsed_seconds(now: datetime, timeframe: Timeframe) -> float:
    """Segundos já decorridos dentro da vela corrente (0 .. duração)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    duration_ms = timeframe_duration_ms(timeframe)
    now_ms = int(now.timestamp() * 1000)
    return (now_ms % duration_ms) / 1000.0


def entry_cutoff_elapsed_seconds(timeframe: Timeframe) -> float:
    """A partir deste elapsed da vela corrente a entrada é bloqueada.

    M1: segundo 55 (comportamento da UI Ebinex).
    Outros TF: últimos 5s da vela (mesma trava de cauda).
    """
    duration = timeframe_duration_seconds(timeframe)
    if timeframe is Timeframe.M1:
        return M1_ENTRY_CUTOFF_ELAPSED_SECONDS
    return max(0.0, duration - ENTRY_LOCKOUT_TAIL_SECONDS)


@dataclass(frozen=True, slots=True)
class EntryWindow:
    """Janela de envio CALL/PUT na vela corrente."""

    now: datetime
    timeframe: Timeframe
    elapsed_seconds: float
    cutoff_seconds: float
    remaining_until_cutoff: float
    open: bool
    reason: str


def entry_window(
    timeframe: Timeframe,
    *,
    now: datetime | None = None,
) -> EntryWindow:
    """Calcula se ainda dá para enviar ordem (botões CALL/PUT visíveis)."""
    clock = now or datetime.now(UTC)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=UTC)
    elapsed = candle_elapsed_seconds(clock, timeframe)
    cutoff = entry_cutoff_elapsed_seconds(timeframe)
    remaining = cutoff - elapsed
    if elapsed >= cutoff:
        return EntryWindow(
            now=clock,
            timeframe=timeframe,
            elapsed_seconds=elapsed,
            cutoff_seconds=cutoff,
            remaining_until_cutoff=0.0,
            open=False,
            reason=(
                f"janela de entrada fechada: elapsed={elapsed:.1f}s >= corte {cutoff:.0f}s "
                f"({timeframe.value}); na Ebinex os botões CALL/PUT somem nesse intervalo"
            ),
        )
    return EntryWindow(
        now=clock,
        timeframe=timeframe,
        elapsed_seconds=elapsed,
        cutoff_seconds=cutoff,
        remaining_until_cutoff=remaining,
        open=True,
        reason=(
            f"janela aberta: elapsed={elapsed:.1f}s, "
            f"~{remaining:.1f}s até o corte {cutoff:.0f}s"
        ),
    )


def assert_entry_window_open(
    timeframe: Timeframe,
    *,
    now: datetime | None = None,
) -> EntryWindow:
    """Levanta ValueError se já passou do segundo de corte."""
    window = entry_window(timeframe, now=now)
    if not window.open:
        raise ValueError(window.reason)
    return window


def expected_schedule(
    timeframe: Timeframe,
    *,
    now: datetime | None = None,
) -> OptionSchedule:
    """Agenda local: open = vela seguinte; settle = fim dessa vela."""
    clock = now or datetime.now(UTC)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=UTC)
    open_at = next_candle_open(clock, timeframe)
    candle_s = timeframe_duration_seconds(timeframe)
    settle_at = datetime.fromtimestamp(open_at.timestamp() + candle_s, tz=UTC)
    return OptionSchedule(
        now=clock,
        timeframe=timeframe,
        open_at=open_at,
        settle_at=settle_at,
        candle_seconds=candle_s,
    )


def schedule_from_order(
    order: Order,
    *,
    now: datetime | None = None,
    fallback_timeframe: Timeframe | None = None,
) -> OptionSchedule:
    """Prefere candleStart/End do broker; cai no cálculo local se faltar."""
    clock = now or datetime.now(UTC)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=UTC)
    tf = order.request.timeframe if order.request else fallback_timeframe
    if tf is None:
        tf = Timeframe.M1

    open_at = order.scheduled_open_at
    settle_at = order.expires_at

    if open_at is None or settle_at is None:
        local = expected_schedule(tf, now=clock)
        open_at = open_at or local.open_at
        settle_at = settle_at or local.settle_at

    if open_at.tzinfo is None:
        open_at = open_at.replace(tzinfo=UTC)
    if settle_at.tzinfo is None:
        settle_at = settle_at.replace(tzinfo=UTC)

    # Se o broker só mandar um dos lados, completa com 1 vela.
    candle_s = timeframe_duration_seconds(tf)
    if settle_at <= open_at:
        settle_at = datetime.fromtimestamp(open_at.timestamp() + candle_s, tz=UTC)

    return OptionSchedule(
        now=clock,
        timeframe=tf,
        open_at=open_at,
        settle_at=settle_at,
        candle_seconds=candle_s,
    )


def settlement_wait_seconds(
    timeframe: Timeframe,
    *,
    order: Order | None = None,
    now: datetime | None = None,
    buffer_seconds: float = DEFAULT_BUFFER_SECONDS,
    floor_seconds: float | None = None,
) -> float:
    """Segundos a esperar pela liquidação (vela seguinte + margem)."""
    if order is not None:
        schedule = schedule_from_order(order, now=now, fallback_timeframe=timeframe)
    else:
        schedule = expected_schedule(timeframe, now=now)
    timeout = schedule.wait_timeout(buffer_seconds=buffer_seconds)
    if floor_seconds is not None:
        timeout = max(timeout, floor_seconds)
    return timeout
