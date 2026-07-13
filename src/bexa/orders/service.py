"""Serviço de ordens (leitura / wait) sobre EbinexClient."""

from __future__ import annotations

from ebinexpy import EbinexClient, Order, OrderQuery, Settlement

from bexa.core.logging import get_logger

log = get_logger("bexa.orders")


class OrderService:
    def __init__(self, client: EbinexClient) -> None:
        self._client = client

    async def list(self, query: OrderQuery | None = None) -> list[Order]:
        orders = await self._client.list_orders(query)
        log.info("ordens listadas count=%s", len(orders))
        return orders

    async def get(self, order_id: str, *, refresh: bool = False) -> Order | None:
        return await self._client.get_order(order_id, refresh=refresh)

    async def wait(
        self,
        order_id: str,
        timeout: float | None = None,  # noqa: ASYNC109 — repassa API do ebinexpy
    ) -> Settlement:
        settlement = await self._client.wait_order(order_id, timeout)
        log.info(
            "settlement order=%s status=%s profit=%s",
            settlement.order.id,
            settlement.order.status.value,
            settlement.profit,
        )
        return settlement
