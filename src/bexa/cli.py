"""CLI: status, ordens manuais e robô automático."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import replace
from decimal import Decimal

from ebinexpy import Direction

from bexa.bot import run_bot
from bexa.config import (
    ALLOW_BOT_TOKEN,
    ALLOW_REAL_TRADING_TOKEN,
    AUTO_REAL_TRADE_TOKEN,
    Settings,
)
from bexa.connection import open_session
from bexa.core.exceptions import BexaError
from bexa.core.logging import get_logger
from bexa.execution.guards import require_demo_gate, require_real_cli_gate
from bexa.market.service import parse_timeframe
from bexa.strategy import available_strategies, create_strategy

log = get_logger("bexa.cli")


def _load_dotenv_if_present() -> None:
    """Carrega .env simples (KEY=VALUE) sem depender de python-dotenv."""
    path = os.environ.get("BEXA_ENV_FILE", ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)


async def cmd_status(_: argparse.Namespace) -> int:
    settings = Settings.from_env()
    async with open_session(settings) as session:
        profile = await session.accounts.profile()
        balance = await session.accounts.balance()
        assets = await session.market.list_assets()
        print(f"perfil: {profile.email} ({profile.display_name or profile.id})")
        print(f"ambiente: {settings.environment.value} allow_real={settings.allow_real_trading}")
        print(f"saldo: {balance.amount} {balance.currency}")
        symbols = ", ".join(a.symbol for a in assets[:20])
        print(f"ativos negociáveis ({len(assets)}): {symbols}")
        print(
            f"bot: strategy={settings.bot_strategy} dry_run={settings.bot_dry_run} "
            f"auto_trade={settings.bot_auto_trade} enabled={settings.bot_enabled}"
        )
        print(f"estratégias: {', '.join(available_strategies())}")
    return 0


async def cmd_demo_order(args: argparse.Namespace) -> int:
    require_demo_gate(os.environ.get("BEXA_ALLOW_DEMO_ORDER"))
    settings = Settings.from_env()
    if settings.environment.value != "TEST":
        raise BexaError("demo-order só roda com BEXA_ENVIRONMENT=TEST")

    async with open_session(settings) as session:
        result = await session.execution.execute_option(
            symbol=args.symbol or settings.default_symbol,
            direction=Direction(args.direction.upper()),
            investment=Decimal(str(args.investment)),
            timeframe=parse_timeframe(args.timeframe or settings.default_timeframe),
            wait_settlement=not args.no_wait,
        )
        _print_result(result)
    return 0


async def cmd_real_order(args: argparse.Namespace) -> int:
    require_real_cli_gate(os.environ.get("BEXA_ALLOW_REAL_ORDER"))
    settings = Settings.from_env()
    if settings.environment.value != "REAL" or not settings.allow_real_trading:
        raise BexaError(
            "real-order exige BEXA_ENVIRONMENT=REAL e "
            f"BEXA_ALLOW_REAL_TRADING={ALLOW_REAL_TRADING_TOKEN}"
        )

    async with open_session(settings) as session:
        result = await session.execution.execute_option(
            symbol=args.symbol or settings.default_symbol,
            direction=Direction(args.direction.upper()),
            investment=Decimal(str(args.investment)),
            timeframe=parse_timeframe(args.timeframe or settings.default_timeframe),
            wait_settlement=not args.no_wait,
        )
        _print_result(result)
    return 0


async def cmd_run(args: argparse.Namespace) -> int:
    """Sobe o robô automático (dry-run por padrão; --live envia ordens)."""
    if os.environ.get("BEXA_ALLOW_BOT", "").strip() != ALLOW_BOT_TOKEN:
        raise BexaError(f"Defina BEXA_ALLOW_BOT={ALLOW_BOT_TOKEN} de propósito para rodar o robô")
    if args.live and args.dry_run:
        raise BexaError("Use --live OU --dry-run, não ambos")

    settings = Settings.from_env()
    dry_run = True
    auto_trade = False
    if args.live:
        dry_run = False
        auto_trade = True
    if args.dry_run:
        dry_run = True
        auto_trade = False

    if args.live and settings.environment.value == "REAL" and not settings.bot_allow_auto_real:
        raise BexaError(
            "Robô LIVE em REAL exige "
            f"BEXA_ALLOW_AUTO_REAL_TRADE={AUTO_REAL_TRADE_TOKEN} "
            f"(além de BEXA_ALLOW_REAL_TRADING={ALLOW_REAL_TRADING_TOKEN})"
        )

    settings = replace(
        settings,
        bot_enabled=True,
        bot_strategy=(args.strategy or settings.bot_strategy).lower(),
        default_symbol=args.symbol or settings.default_symbol,
        default_timeframe=args.timeframe or settings.default_timeframe,
        bot_dry_run=dry_run,
        bot_auto_trade=auto_trade,
        bot_max_trades=args.max_trades if args.max_trades is not None else settings.bot_max_trades,
        bot_default_investment=(
            Decimal(str(args.investment))
            if args.investment is not None
            else settings.bot_default_investment
        ),
    )
    strategy = create_strategy(settings.bot_strategy)
    log.info(
        "bexa run strategy=%s dry_run=%s auto_trade=%s symbol=%s tf=%s",
        settings.bot_strategy,
        settings.bot_dry_run,
        settings.bot_auto_trade,
        settings.default_symbol,
        settings.default_timeframe,
    )
    if args.live and settings.environment.value == "REAL":
        log.warning("ATENÇÃO: robô LIVE em conta REAL")
    return await run_bot(settings, strategy=strategy)


def _print_result(result: object) -> None:
    order = getattr(result, "order", None)
    settlement = getattr(result, "settlement", None)
    schedule = getattr(result, "schedule", None)
    wait_timeout = getattr(result, "wait_timeout_seconds", None)
    if order is not None:
        print(f"order_id={order.id} status={order.status.value}")
    if schedule is not None:
        print(
            "agenda: entrada na vela seguinte "
            f"open_at={schedule.open_at.isoformat()} "
            f"settle_at={schedule.settle_at.isoformat()} "
            f"(~{schedule.seconds_until_open:.0f}s abrir / "
            f"~{schedule.seconds_until_settle:.0f}s liquidar)"
        )
    if wait_timeout is not None:
        print(f"wait_timeout={wait_timeout:.0f}s")
    if settlement is not None:
        print(f"settlement status={settlement.order.status.value} profit={settlement.profit}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bexa", description="CLI bexa / Ebinex")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Perfil, saldo e ativos (somente leitura)")

    demo = sub.add_parser("demo-order", help="Uma ordem TEST (gate BEXA_ALLOW_DEMO_ORDER)")
    demo.add_argument("--symbol", default="")
    demo.add_argument("--direction", default="CALL", choices=["CALL", "PUT", "call", "put"])
    demo.add_argument("--investment", default="1")
    demo.add_argument("--timeframe", default="")
    demo.add_argument("--no-wait", action="store_true")

    real = sub.add_parser("real-order", help="Uma ordem REAL (triplo opt-in)")
    real.add_argument("--symbol", default="")
    real.add_argument("--direction", default="CALL", choices=["CALL", "PUT", "call", "put"])
    real.add_argument("--investment", default="1")
    real.add_argument("--timeframe", default="")
    real.add_argument("--no-wait", action="store_true")

    run = sub.add_parser(
        "run",
        help=f"Robô automático (dry-run por padrão; exige BEXA_ALLOW_BOT={ALLOW_BOT_TOKEN})",
    )
    run.add_argument(
        "--strategy",
        default="",
        help=f"Estratégia: {', '.join(available_strategies())}",
    )
    run.add_argument("--symbol", default="")
    run.add_argument("--timeframe", default="")
    run.add_argument("--investment", default=None)
    run.add_argument("--max-trades", type=int, default=None)
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Força dry-run (não envia ordens)",
    )
    run.add_argument(
        "--live",
        action="store_true",
        help=(
            "Desliga dry-run e liga auto_trade. "
            f"Em REAL exige BEXA_ALLOW_AUTO_REAL_TRADE={AUTO_REAL_TRADE_TOKEN}"
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    _load_dotenv_if_present()
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "status": cmd_status,
        "demo-order": cmd_demo_order,
        "real-order": cmd_real_order,
        "run": cmd_run,
    }
    handler = handlers[args.command]

    try:
        code = asyncio.run(handler(args))
    except BexaError as exc:
        log.error("%s", exc)
        print(f"erro: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except KeyboardInterrupt:
        log.warning("interrompido pelo usuário")
        raise SystemExit(130) from None
    except Exception as exc:  # noqa: BLE001 — CLI surface
        log.exception("falha inesperada")
        print(f"erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
