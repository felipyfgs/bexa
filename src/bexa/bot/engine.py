"""Motor do robô: stream de velas → estratégia → risco → execução."""

from __future__ import annotations

import asyncio
import signal
from collections import deque
from datetime import datetime
from decimal import Decimal

from ebinexpy import Candle

from bexa.config import (
    ALLOW_BOT_TOKEN,
    ALLOW_REAL_TRADING_TOKEN,
    AUTO_REAL_TRADE_TOKEN,
    Settings,
)
from bexa.connection.session import Session, open_session
from bexa.core.exceptions import BexaError, ExecutionGuardError, RiskLimitError
from bexa.core.logging import get_logger
from bexa.execution.models import TradeIntent
from bexa.execution.timing import entry_window
from bexa.market.service import history_lookback_minutes, parse_timeframe
from bexa.risk.models import RiskDecision
from bexa.risk.service import RiskService
from bexa.strategy.base import Strategy
from bexa.strategy.models import BarContext, Signal
from bexa.strategy.registry import create_strategy

log = get_logger("bexa.bot")


class BotEngine:
    """Loop automático alinhado ao ciclo OPTION (sinal na vela N, entra na N+1)."""

    def __init__(
        self,
        settings: Settings,
        strategy: Strategy | None = None,
        *,
        session: Session | None = None,
    ) -> None:
        self.settings = settings
        self.strategy = strategy or create_strategy(settings.bot_strategy)
        self._external_session = session
        self.risk = RiskService(settings)
        self._stop = asyncio.Event()
        self._history: deque[Candle] = deque(maxlen=settings.bot_history_size)
        self._symbol = settings.default_symbol
        self._timeframe = parse_timeframe(settings.default_timeframe)
        # Tasks de settlement fire-and-forget (bot_wait_settlement=False).
        self._settlement_tasks: set[asyncio.Task[None]] = set()

    def request_stop(self, reason: str = "stop solicitado") -> None:
        log.warning("robô parando: %s", reason)
        self._stop.set()

    async def run(self) -> int:
        self._validate_run_config()
        log.info(
            "iniciando robô strategy=%s symbol=%s tf=%s dry_run=%s auto_trade=%s env=%s",
            getattr(self.strategy, "name", type(self.strategy).__name__),
            self._symbol,
            self._timeframe.value,
            self.settings.bot_dry_run,
            self.settings.bot_auto_trade,
            self.settings.environment.value,
        )

        owns_session = self._external_session is None
        session = self._external_session or open_session(self.settings)

        loop = asyncio.get_running_loop()
        for sig_name in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig_name, lambda s=sig_name: self.request_stop(s.name))
            except NotImplementedError:
                # Windows / ambientes sem signal handlers no loop
                pass

        try:
            if owns_session:
                await session.__aenter__()
            await self._run_with_session(session)
        finally:
            await self._drain_settlement_tasks()
            if owns_session:
                await session.__aexit__(None, None, None)
            on_stop = getattr(self.strategy, "on_stop", None)
            if callable(on_stop):
                await on_stop()

        log.info(
            "robô finalizado trades=%s settled=%s pnl=%s reason=%s",
            self.risk.state.trades_opened,
            self.risk.state.trades_settled,
            self.risk.state.realized_pnl,
            self.risk.state.stopped_reason or "ok",
        )
        return 0

    def _validate_run_config(self) -> None:
        if not self.settings.bot_enabled:
            raise BexaError(
                f"Robô desligado. Defina BEXA_BOT_ENABLED=YES e BEXA_ALLOW_BOT={ALLOW_BOT_TOKEN}"
            )
        if self.settings.bot_auto_trade and self.settings.bot_dry_run:
            log.warning("auto_trade=True com dry_run=True → nenhum envio real de ordem")
        if (
            self.settings.bot_auto_trade
            and not self.settings.bot_dry_run
            and self.settings.environment.value == "REAL"
        ):
            if not self.settings.allow_real_trading:
                raise BexaError(
                    f"auto_trade REAL exige BEXA_ALLOW_REAL_TRADING={ALLOW_REAL_TRADING_TOKEN}"
                )
            if not self.settings.bot_allow_auto_real:
                raise BexaError(
                    "auto_trade LIVE em REAL exige "
                    f"BEXA_ALLOW_AUTO_REAL_TRADE={AUTO_REAL_TRADE_TOKEN}"
                )

    async def _run_with_session(self, session: Session) -> None:
        on_start = getattr(self.strategy, "on_start", None)
        if callable(on_start):
            await on_start()

        balance = await session.accounts.balance()
        log.info("saldo inicial=%s %s", balance.amount, balance.currency)

        # Pré-aquece histórico REST (lookback proporcional ao timeframe).
        try:
            lookback = history_lookback_minutes(self._timeframe, self.settings.bot_history_size)
            seed = await session.market.get_candles(
                self._symbol,
                self._timeframe,
                lookback_minutes=lookback,
                limit=self.settings.bot_history_size,
            )
            for candle in seed:
                self._history.append(candle)
            log.info(
                "histórico seed=%s velas (lookback=%s min, tf=%s)",
                len(self._history),
                lookback,
                self._timeframe.value,
            )
        except Exception as exc:  # noqa: BLE001 — seed não é crítico
            log.warning("falha ao carregar histórico seed: %s", exc)

        stream = await session.client.stream_candles(self._symbol, self._timeframe)
        last_open: datetime | None = None
        current: Candle | None = None

        async with stream:
            async for event in stream:
                if self._stop.is_set() or self.risk.should_stop():
                    break

                candle = event.candle
                if last_open is not None and candle.open_time != last_open and current is not None:
                    # Rolou vela: `current` fechou.
                    # history no BarContext = velas anteriores (sem o closed atual).
                    await self._on_closed_bar(session, current)
                    self._history.append(current)

                    if self._stop.is_set() or self.risk.should_stop():
                        break

                last_open = candle.open_time
                current = candle

        if self.risk.should_stop() and self.risk.state.stopped_reason:
            log.warning("stop de risco: %s", self.risk.state.stopped_reason)

    async def _on_closed_bar(self, session: Session, closed: Candle) -> None:
        broker = session.client.get_broker_time()
        try:
            balance = await session.accounts.balance()
            bal_amt = balance.amount
        except Exception:  # noqa: BLE001
            bal_amt = None

        # Contrato: history = velas já fechadas anteriores; closed = vela recém-fechada.
        context = BarContext(
            symbol=self._symbol,
            timeframe=self._timeframe,
            closed=closed,
            history=tuple(self._history),
            broker_time=broker.value if broker else None,
            balance=bal_amt,
        )

        log.info(
            "vela fechada %s %s open=%s close=%s",
            self._symbol,
            closed.open_time.isoformat(),
            closed.open,
            closed.close,
        )

        try:
            signal = await self.strategy.on_bar_close(context)
        except Exception:
            log.exception("estratégia falhou em on_bar_close")
            return

        if signal is None:
            log.info("sem sinal")
            return

        await self._handle_signal(session, signal, closed)

    async def _handle_signal(self, session: Session, signal: Signal, closed: Candle) -> None:
        symbol = signal.symbol or self._symbol
        timeframe = signal.timeframe or self._timeframe
        investment = signal.investment or self.settings.bot_default_investment

        # Fail-closed: stake acima do max é rejeitado, não clamado em silêncio.
        if investment > self.settings.max_investment:
            decision = RiskDecision(
                False,
                f"investment {investment} > max {self.settings.max_investment}",
            )
            log.warning("risco bloqueou: %s", decision.reason)
            return

        log.info(
            "sinal %s %s %s stake=%s reason=%s",
            signal.direction.value,
            symbol,
            timeframe.value,
            investment,
            signal.reason or "-",
        )

        decision = self.risk.evaluate_signal(signal, investment)
        if not decision.allowed:
            log.warning("risco bloqueou: %s", decision.reason)
            return

        # Mesmo com sinal, se já passou do s:55 (M1) a UI some CALL/PUT — não envia.
        broker = session.client.get_broker_time()
        clock = broker.value if broker is not None else None
        window = entry_window(timeframe, now=clock)
        if not window.open:
            log.warning("entrada bloqueada (corte Ebinex): %s", window.reason)
            return
        log.info("janela de entrada: %s", window.reason)

        if self.settings.bot_dry_run or not self.settings.bot_auto_trade:
            log.info(
                "DRY-RUN (não envia ordem) dry_run=%s auto_trade=%s",
                self.settings.bot_dry_run,
                self.settings.bot_auto_trade,
            )
            # Conta sinal dry-run no limite da sessão para poder encerrar com max-trades.
            self.risk.on_order_submitted()
            self.risk.on_order_settled(Decimal("0"))
            return

        intent = TradeIntent(
            symbol=symbol,
            direction=signal.direction,
            investment=investment,
            timeframe=timeframe,
            price=closed.close,
            wait_settlement=self.settings.bot_wait_settlement,
        )

        try:
            result = await session.execution.execute(intent)
        except (ExecutionGuardError, RiskLimitError, BexaError) as exc:
            log.error("execução bloqueada: %s", exc)
            return
        except Exception:
            log.exception("falha ao executar ordem")
            return

        self.risk.on_order_submitted()
        if result.settlement is not None:
            profit = result.settlement.profit or Decimal("0")
            self.risk.on_order_settled(profit)
            log.info(
                "trade liquidado status=%s profit=%s",
                result.settlement.order.status.value,
                profit,
            )
        elif not self.settings.bot_wait_settlement:
            # Fire-and-forget: acompanha em background (task registrada).
            task = asyncio.create_task(
                self._track_settlement(session, result.order.id),
                name=f"settlement:{result.order.id}",
            )
            self._settlement_tasks.add(task)
            task.add_done_callback(self._settlement_tasks.discard)

    async def _track_settlement(self, session: Session, order_id: str) -> None:
        try:
            settlement = await session.orders.wait(order_id)
            profit = settlement.profit or Decimal("0")
            self.risk.on_order_settled(profit)
            log.info(
                "track settlement id=%s status=%s profit=%s",
                order_id,
                settlement.order.status.value,
                profit,
            )
        except Exception:
            log.exception("falha ao acompanhar settlement id=%s", order_id)
            # libera slot de open order para não travar o robô
            self.risk.state.open_orders = max(0, self.risk.state.open_orders - 1)

    async def _drain_settlement_tasks(self, timeout_seconds: float = 30.0) -> None:
        """Aguarda (ou cancela) tasks de settlement antes de fechar a sessão."""
        pending = {t for t in self._settlement_tasks if not t.done()}
        if not pending:
            return
        log.info(
            "aguardando %s settlement(s) em background (timeout=%.0fs)",
            len(pending),
            timeout_seconds,
        )
        done, still = await asyncio.wait(pending, timeout=timeout_seconds)
        for task in still:
            task.cancel()
        if still:
            await asyncio.gather(*still, return_exceptions=True)
            log.warning("cancelou %s settlement(s) pendente(s) no shutdown", len(still))
        # Garante que exceções de tasks concluídas não fiquem "unretrieved".
        for task in done:
            if task.cancelled():
                continue
            exc = task.exception()
            if exc is not None:
                log.error("settlement task falhou no shutdown: %s", exc)


async def run_bot(settings: Settings | None = None, strategy: Strategy | None = None) -> int:
    cfg = settings or Settings.from_env()
    engine = BotEngine(cfg, strategy=strategy)
    return await engine.run()
