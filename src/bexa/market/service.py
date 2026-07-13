"""Serviço de mercado (ativos, payout, candles, preço live)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ebinexpy import Asset, Candle, EbinexClient, Timeframe

from bexa.core.exceptions import BexaError
from bexa.core.logging import get_logger
from bexa.execution.timing import timeframe_duration_seconds

log = get_logger("bexa.market")

DEFAULT_SNAPSHOT_TIMEOUT = 15.0


def parse_timeframe(value: str | Timeframe) -> Timeframe:
    if isinstance(value, Timeframe):
        return value
    try:
        return Timeframe(value.upper())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Timeframe)
        raise ValueError(f"timeframe inválido: {value!r}. Use: {allowed}") from exc


def history_lookback_minutes(timeframe: Timeframe, candle_count: int, *, margin: int = 2) -> int:
    """Converte contagem de velas em minutos de lookback REST (com margem)."""
    candle_minutes = max(1, int(timeframe_duration_seconds(timeframe) // 60))
    return max(5, candle_count * candle_minutes + margin * candle_minutes)


class MarketService:
    def __init__(self, client: EbinexClient) -> None:
        self._client = client

    async def list_assets(
        self, *, refresh: bool = False, tradable_only: bool = True
    ) -> list[Asset]:
        assets = await self._client.list_assets(refresh=refresh)
        if tradable_only:
            assets = [a for a in assets if a.tradable]
        return assets

    async def get_asset(self, symbol: str, *, refresh: bool = False) -> Asset:
        return await self._client.get_asset(symbol, refresh=refresh)

    async def get_payout(self, symbol: str, timeframe: str | Timeframe) -> Decimal:
        tf = parse_timeframe(timeframe)
        return await self._client.get_payout(symbol, tf)

    async def is_market_open(self, symbol: str, timeframe: str | Timeframe) -> bool:
        tf = parse_timeframe(timeframe)
        return await self._client.is_market_open(symbol, tf)

    async def assert_tradable(
        self, symbol: str, timeframe: str | Timeframe, *, refresh: bool = False
    ) -> Asset:
        """Pré-valida símbolo/timeframe/mercado aberto antes de snapshot ou ordem."""
        tf = parse_timeframe(timeframe)
        asset = await self.get_asset(symbol, refresh=refresh)
        if not asset.tradable:
            raise BexaError(f"Ativo {symbol} não está negociável (status={asset.status})")
        if asset.timeframes and tf not in asset.timeframes:
            allowed = ", ".join(t.value for t in asset.timeframes) or "(vazio)"
            raise BexaError(
                f"Timeframe {tf.value} não suportado para {symbol}. Disponíveis: {allowed}"
            )
        if not await self.is_market_open(symbol, tf):
            raise BexaError(f"Mercado fechado para {symbol} {tf.value}")
        return asset

    async def get_candles(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        *,
        lookback_minutes: int = 60,
        limit: int = 500,
    ) -> list[Candle]:
        tf = parse_timeframe(timeframe)
        end = datetime.now(UTC)
        start = end - timedelta(minutes=lookback_minutes)
        return await self._client.get_candles(symbol, tf, start, end, limit=limit)

    async def snapshot_price(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        *,
        timeout_seconds: float = DEFAULT_SNAPSHOT_TIMEOUT,
    ) -> Decimal:
        """Obtém preço de fechamento recente via stream de candles (1 tick)."""
        tf = parse_timeframe(timeframe)
        stream = await self._client.stream_candles(symbol, tf)
        try:
            async with stream:
                event = await asyncio.wait_for(stream.__anext__(), timeout=timeout_seconds)
        except TimeoutError as exc:
            raise BexaError(
                f"Timeout ({timeout_seconds:.0f}s) aguardando preço de {symbol} {tf.value} "
                "(stream de candles sem tick)"
            ) from exc
        except StopAsyncIteration as exc:
            raise BexaError(
                f"Stream de candles de {symbol} {tf.value} encerrou sem eventos"
            ) from exc
        price = event.candle.close
        log.info("preço %s %s = %s", symbol, tf.value, price)
        return price

    async def stream_candles(self, symbol: str, timeframe: str | Timeframe):
        """Proxy tipado do stream de candles do ebinexpy."""
        tf = parse_timeframe(timeframe)
        return await self._client.stream_candles(symbol, tf)

    async def stream_ticker(self, symbol: str, timeframe: str | Timeframe):
        tf = parse_timeframe(timeframe)
        return await self._client.stream_ticker(symbol, tf)

    async def stream_book(self, symbol: str, timeframe: str | Timeframe):
        tf = parse_timeframe(timeframe)
        return await self._client.stream_book(symbol, tf)
