"""Serviço de contas sobre EbinexClient."""

from __future__ import annotations

from ebinexpy import Account, AccountEnvironment, Balance, EbinexClient, Profile

from bexa.core.logging import get_logger

log = get_logger("bexa.accounts")


class AccountService:
    def __init__(self, client: EbinexClient) -> None:
        self._client = client

    async def list(self) -> list[Account]:
        accounts = await self._client.list_accounts()
        log.info("contas=%s", [(a.environment.value, str(a.balance)) for a in accounts])
        return accounts

    async def select(self, environment: AccountEnvironment) -> Account:
        account = await self._client.select_account(environment)
        log.info("conta selecionada id=%s env=%s", account.id, account.environment.value)
        return account

    async def profile(self) -> Profile:
        return await self._client.get_profile()

    async def balance(self) -> Balance:
        balance = await self._client.get_balance()
        log.info("saldo=%s %s", balance.amount, balance.currency)
        return balance
