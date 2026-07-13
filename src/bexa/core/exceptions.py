"""Hierarquia de erros do bexa (camada app; ebinexpy tem a própria)."""


class BexaError(Exception):
    """Erro base da aplicação bexa."""


class ConfigError(BexaError):
    """Configuração inválida ou incompleta."""


class ExecutionGuardError(BexaError):
    """Bloqueio de segurança antes de enviar ordem."""


class RiskLimitError(ExecutionGuardError):
    """Violação de limite de risco (stake, etc.)."""
