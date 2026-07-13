"""Feature: estratégias pluggable para o robô."""

from .base import Strategy
from .models import BarContext, Signal
from .registry import available_strategies, create_strategy, register_strategy

__all__ = [
    "BarContext",
    "Signal",
    "Strategy",
    "available_strategies",
    "create_strategy",
    "register_strategy",
]
