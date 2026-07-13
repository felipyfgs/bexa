"""bexa — camada de aplicação modular sobre ebinexpy."""

from .bot import BotEngine, run_bot
from .config import Settings
from .connection import create_client, open_session
from .execution import ExecutionService, TradeIntent, TradeResult

__all__ = [
    "BotEngine",
    "ExecutionService",
    "Settings",
    "TradeIntent",
    "TradeResult",
    "create_client",
    "open_session",
    "run_bot",
]

__version__ = "0.1.0"
