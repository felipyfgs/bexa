"""Ciclo de vida da sessão (connect / close) e composição de features."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from ebinexpy import EbinexClient

from bexa.accounts.service import AccountService
from bexa.config import Settings
from bexa.connection.factory import create_client
from bexa.core.logging import get_logger
from bexa.execution.service import ExecutionService
from bexa.market.service import MarketService
from bexa.orders.service import OrderService

log = get_logger("bexa.connection")


class Session:
    """Sessão pronta com services por feature."""

    def __init__(self, settings: Settings, client: EbinexClient) -> None:
        self.settings = settings
        self.client = client
        self.accounts = AccountService(client)
        self.market = MarketService(client)
        self.orders = OrderService(client)
        self.execution = ExecutionService(client, settings, self.market)

    async def __aenter__(self) -> Self:
        await self.client.connect()
        await self.client.wait_until_ready(timeout=self.settings.connect_timeout)
        log.info(
            "sessão pronta authenticated=%s connected=%s env=%s",
            self.client.authenticated,
            self.client.connected,
            self.settings.environment.value,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.client.close()
        log.info("sessão encerrada")


def open_session(settings: Settings | None = None) -> Session:
    """Cria Session (use como async context manager)."""
    cfg = settings or Settings.from_env()
    return Session(cfg, create_client(cfg))
