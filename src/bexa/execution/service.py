"""Execução de ordens OPTION na Ebinex via ebinexpy."""

from __future__ import annotations

from decimal import Decimal

from ebinexpy import Direction, EbinexClient, OrderRequest, Timeframe

from bexa.config import Settings
from bexa.core.logging import get_logger
from bexa.execution.guards import as_money, assert_can_execute
from bexa.execution.models import TradeIntent, TradeResult
from bexa.execution.timing import entry_window, schedule_from_order, settlement_wait_seconds
from bexa.market.service import MarketService, parse_timeframe

log = get_logger("bexa.execution")


class ExecutionService:
    """Orquestra preço → validação → place_order → wait_order.

    Ciclo Ebinex (OPTION):
    - envio só enquanto a janela de entrada estiver aberta (M1: antes do s:55);
    - entrada na **vela seguinte** → liquidação no **fim** dessa vela.
    O wait usa esse horizonte (até ~2× timeframe + margem), não um timeout fixo curto.
    """

    def __init__(
        self,
        client: EbinexClient,
        settings: Settings,
        market: MarketService | None = None,
    ) -> None:
        self._client = client
        self._settings = settings
        self._market = market or MarketService(client)

    async def execute(self, intent: TradeIntent) -> TradeResult:
        assert_can_execute(self._client, self._settings, intent)

        # Pré-checagem de mercado (falha cedo, com erro bexa, antes do stream).
        await self._market.assert_tradable(intent.symbol, intent.timeframe)

        price = intent.price
        if price is None:
            price = await self._market.snapshot_price(
                intent.symbol,
                intent.timeframe,
                timeout_seconds=self._settings.connect_timeout,
            )

        request = OrderRequest(
            symbol=intent.symbol,
            direction=intent.direction,
            investment=intent.investment,
            timeframe=intent.timeframe,
            price=price,
        )

        env = (
            self._client.accounts.selected.environment.value
            if self._client.accounts.selected
            else "?"
        )
        broker = self._client.get_broker_time()
        clock = broker.value if broker is not None else None
        window = entry_window(intent.timeframe, now=clock)
        log.warning(
            "enviando ordem env=%s symbol=%s dir=%s stake=%s tf=%s price=%s "
            "(%s; entrada=vela seguinte; liquidação=fim da vela seguinte)",
            env,
            request.symbol,
            request.direction.value,
            request.investment,
            request.timeframe.value,
            request.price,
            window.reason,
        )

        order = await self._client.place_order(request)
        schedule = schedule_from_order(order, fallback_timeframe=intent.timeframe)
        log.info(
            "ordem aceita id=%s status=%s open_at=%s settle_at=%s "
            "(~%.0fs até abrir, ~%.0fs até liquidar)",
            order.id,
            order.status.value,
            schedule.open_at.isoformat(),
            schedule.settle_at.isoformat(),
            schedule.seconds_until_open,
            schedule.seconds_until_settle,
        )

        settlement = None
        wait_timeout: float | None = None
        if intent.wait_settlement:
            # Preferência: horizonte da vela seguinte + margem; floor = setting.
            wait_timeout = settlement_wait_seconds(
                intent.timeframe,
                order=order,
                buffer_seconds=self._settings.settlement_buffer_seconds,
                floor_seconds=self._settings.settlement_timeout,
            )
            log.info(
                "aguardando liquidação id=%s timeout=%.0fs (schedule+buffer, floor=%.0fs)",
                order.id,
                wait_timeout,
                self._settings.settlement_timeout,
            )
            settlement = await self._client.wait_order(order.id, timeout=wait_timeout)
            log.info(
                "ordem liquidada id=%s status=%s profit=%s",
                settlement.order.id,
                settlement.order.status.value,
                settlement.profit,
            )

        return TradeResult(
            order=order,
            settlement=settlement,
            schedule=schedule,
            wait_timeout_seconds=wait_timeout,
        )

    async def execute_option(
        self,
        *,
        symbol: str,
        direction: Direction | str,
        investment: Decimal | str | int | float,
        timeframe: Timeframe | str | None = None,
        price: Decimal | None = None,
        wait_settlement: bool = True,
    ) -> TradeResult:
        """Atalho com tipos flexíveis para CLI e scripts."""
        dir_ = direction if isinstance(direction, Direction) else Direction(str(direction).upper())
        tf = parse_timeframe(timeframe or self._settings.default_timeframe)
        intent = TradeIntent(
            symbol=symbol,
            direction=dir_,
            investment=as_money(investment),
            timeframe=tf,
            price=price,
            wait_settlement=wait_settlement,
        )
        return await self.execute(intent)
