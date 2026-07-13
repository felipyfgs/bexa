"""Factory do EbinexClient a partir de Settings do bexa."""

from __future__ import annotations

from ebinexpy import ClientConfig, EbinexClient

from bexa.config import Settings
from bexa.core.logging import get_logger

log = get_logger("bexa.connection")


def create_client(settings: Settings) -> EbinexClient:
    """Cria o client sem conectar.

    Para REAL, `allow_real_trading` já foi validado em Settings e é repassado
    ao ClientConfig (gate obrigatório do ebinexpy).
    """
    if settings.session_dir is not None:
        config = ClientConfig.with_file_sessions(
            settings.session_dir,
            environment=settings.environment,
            allow_real_trading=settings.allow_real_trading,
            connect_timeout=settings.connect_timeout,
            settlement_timeout=settings.settlement_timeout,
        )
    else:
        config = ClientConfig(
            environment=settings.environment,
            allow_real_trading=settings.allow_real_trading,
            connect_timeout=settings.connect_timeout,
            settlement_timeout=settings.settlement_timeout,
        )

    log.info(
        "client configurado env=%s allow_real=%s session_store=%s",
        settings.environment.value,
        settings.allow_real_trading,
        "file" if settings.session_dir else "memory",
    )
    return EbinexClient(settings.email, settings.password, config)
