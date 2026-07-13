"""Configuração do bexa a partir de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ebinexpy import AccountEnvironment

from bexa.core.exceptions import ConfigError

# Literais fortes de opt-in (difíceis de digitar por acidente).
ALLOW_REAL_TRADING_TOKEN = "YES_REAL_TRADING"
ALLOW_BOT_TOKEN = "YES_RUN_BOT"
AUTO_TRADE_TOKEN = "YES_AUTO_TRADE"
AUTO_REAL_TRADE_TOKEN = "YES_AUTO_REAL_TRADE"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _parse_environment(raw: str) -> AccountEnvironment:
    value = (raw or "TEST").upper()
    try:
        return AccountEnvironment(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AccountEnvironment)
        raise ConfigError(f"BEXA_ENVIRONMENT inválido: {raw!r}. Use um de: {allowed}") from exc


def _parse_exact_token(raw: str, token: str) -> bool:
    """True somente se o valor (após strip) for exatamente o token (case-sensitive)."""
    return raw.strip() == token


def _parse_bool_default_true(raw: str) -> bool:
    """True por padrão; desliga com 0/false/no/off."""
    return raw.strip().upper() not in {"0", "FALSE", "NO", "OFF"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuração imutável do processo bexa.

    Credenciais ficam aqui (não em ClientConfig do ebinexpy) para o app carregar
    de env; o ClientConfig recebe só environment/allow_real_trading/session.
    """

    email: str
    password: str
    environment: AccountEnvironment = AccountEnvironment.TEST
    allow_real_trading: bool = False
    session_dir: Path | None = None
    max_investment: Decimal = Decimal("10")
    default_symbol: str = "IDXUSDT"
    default_timeframe: str = "M1"
    connect_timeout: float = 15.0
    # Floor mínimo do wait. O timeout efetivo é max(floor, até fim da vela
    # seguinte + buffer) — ver execution/timing.py.
    settlement_timeout: float = 130.0
    # Margem além do fim da vela de execução (rede + evento WS + reconcile).
    settlement_buffer_seconds: float = 20.0

    # --- Robô automático ---
    # bot_enabled exige BEXA_BOT_ENABLED + gate BEXA_ALLOW_BOT (ver from_env).
    bot_enabled: bool = False
    bot_strategy: str = "hold"
    # dry_run=True: gera sinais e aplica risco, mas NÃO envia ordem.
    bot_dry_run: bool = True
    # auto_trade=True: permite envio real (ainda respeita dry_run e ambiente).
    # Só ativa com literal YES_AUTO_TRADE (não 1/TRUE/YES genéricos).
    bot_auto_trade: bool = False
    # Opt-in extra para auto-trade em conta REAL (YES_AUTO_REAL_TRADE).
    bot_allow_auto_real: bool = False
    bot_default_investment: Decimal = Decimal("1")
    bot_max_trades: int = 20
    bot_max_open_orders: int = 1
    bot_cooldown_seconds: float = 5.0
    bot_max_daily_loss: Decimal = Decimal("0")  # 0 = desligado
    bot_history_size: int = 50
    # Se True, espera liquidação antes do próximo trade (mais seguro).
    # False = fire-and-forget avançado (tasks rastreadas no shutdown).
    bot_wait_settlement: bool = True

    def __post_init__(self) -> None:
        if not self.email:
            raise ConfigError("EBINEX_EMAIL é obrigatório")
        if not self.password:
            raise ConfigError("EBINEX_PASSWORD é obrigatório")
        if self.max_investment <= 0:
            raise ConfigError("BEXA_MAX_INVESTMENT deve ser positivo")
        if self.settlement_timeout <= 0:
            raise ConfigError("BEXA_SETTLEMENT_TIMEOUT deve ser positivo")
        if self.settlement_buffer_seconds < 0:
            raise ConfigError("BEXA_SETTLEMENT_BUFFER_SECONDS não pode ser negativo")
        if self.bot_default_investment <= 0:
            raise ConfigError("BEXA_BOT_INVESTMENT deve ser positivo")
        if self.bot_max_trades < 1:
            raise ConfigError("BEXA_BOT_MAX_TRADES deve ser >= 1")
        if self.bot_max_open_orders < 1:
            raise ConfigError("BEXA_BOT_MAX_OPEN_ORDERS deve ser >= 1")
        if self.bot_history_size < 1:
            raise ConfigError("BEXA_BOT_HISTORY_SIZE deve ser >= 1")
        if self.connect_timeout <= 0:
            raise ConfigError("BEXA_CONNECT_TIMEOUT deve ser positivo")
        if self.environment is AccountEnvironment.REAL and not self.allow_real_trading:
            raise ConfigError(
                f"Conta REAL exige BEXA_ALLOW_REAL_TRADING={ALLOW_REAL_TRADING_TOKEN} "
                "(opt-in explícito; nunca use REAL por acidente)"
            )
        # Auto-trade em REAL sem dry-run exige token dedicado.
        if (
            self.bot_auto_trade
            and not self.bot_dry_run
            and self.environment is AccountEnvironment.REAL
            and not self.bot_allow_auto_real
        ):
            raise ConfigError(
                "Auto-trade LIVE em REAL exige "
                f"BEXA_ALLOW_AUTO_REAL_TRADE={AUTO_REAL_TRADE_TOKEN} "
                f"(além de BEXA_ALLOW_REAL_TRADING={ALLOW_REAL_TRADING_TOKEN})"
            )

    @classmethod
    def from_env(cls) -> Settings:
        session_raw = _env("BEXA_SESSION_DIR")
        max_raw = _env("BEXA_MAX_INVESTMENT", "10")
        # BEXA_BOT_ENABLED aceita YES genérico (só liga se o gate forte também existir).
        bot_flag = _env("BEXA_BOT_ENABLED").upper() in {"1", "TRUE", "YES", "ON"}
        bot_gate = _parse_exact_token(_env("BEXA_ALLOW_BOT"), ALLOW_BOT_TOKEN)
        # Aliases legados BEXA_SYMBOL / BEXA_TIMEFRAME (docs antigas).
        symbol = _env("BEXA_DEFAULT_SYMBOL") or _env("BEXA_SYMBOL") or "IDXUSDT"
        timeframe = _env("BEXA_DEFAULT_TIMEFRAME") or _env("BEXA_TIMEFRAME") or "M1"
        return cls(
            email=_env("EBINEX_EMAIL"),
            password=_env("EBINEX_PASSWORD"),
            environment=_parse_environment(_env("BEXA_ENVIRONMENT", "TEST")),
            allow_real_trading=_parse_exact_token(
                _env("BEXA_ALLOW_REAL_TRADING"),
                ALLOW_REAL_TRADING_TOKEN,
            ),
            session_dir=Path(session_raw).expanduser() if session_raw else None,
            max_investment=Decimal(max_raw),
            default_symbol=symbol,
            default_timeframe=timeframe,
            connect_timeout=float(_env("BEXA_CONNECT_TIMEOUT", "15") or "15"),
            # M1 pior caso ≈ 2×60s + buffer; 130s como piso seguro.
            settlement_timeout=float(_env("BEXA_SETTLEMENT_TIMEOUT", "130") or "130"),
            settlement_buffer_seconds=float(_env("BEXA_SETTLEMENT_BUFFER_SECONDS", "20") or "20"),
            bot_enabled=bot_flag and bot_gate,
            bot_strategy=(_env("BEXA_BOT_STRATEGY", "hold") or "hold").lower(),
            bot_dry_run=_parse_bool_default_true(_env("BEXA_BOT_DRY_RUN", "1")),
            bot_auto_trade=_parse_exact_token(
                _env("BEXA_BOT_AUTO_TRADE"),
                AUTO_TRADE_TOKEN,
            ),
            bot_allow_auto_real=_parse_exact_token(
                _env("BEXA_ALLOW_AUTO_REAL_TRADE"),
                AUTO_REAL_TRADE_TOKEN,
            ),
            bot_default_investment=Decimal(_env("BEXA_BOT_INVESTMENT", "1") or "1"),
            bot_max_trades=int(_env("BEXA_BOT_MAX_TRADES", "20") or "20"),
            bot_max_open_orders=int(_env("BEXA_BOT_MAX_OPEN_ORDERS", "1") or "1"),
            bot_cooldown_seconds=float(_env("BEXA_BOT_COOLDOWN_SECONDS", "5") or "5"),
            bot_max_daily_loss=Decimal(_env("BEXA_BOT_MAX_DAILY_LOSS", "0") or "0"),
            bot_history_size=int(_env("BEXA_BOT_HISTORY_SIZE", "50") or "50"),
            bot_wait_settlement=_parse_bool_default_true(_env("BEXA_BOT_WAIT_SETTLEMENT", "1")),
        )
