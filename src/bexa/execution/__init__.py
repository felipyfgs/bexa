"""Feature: execução de ordens OPTION (TEST e REAL com gates)."""

from .guards import assert_can_execute
from .models import TradeIntent, TradeResult
from .service import ExecutionService
from .timing import (
    EntryWindow,
    OptionSchedule,
    entry_window,
    expected_schedule,
    settlement_wait_seconds,
)

__all__ = [
    "EntryWindow",
    "ExecutionService",
    "OptionSchedule",
    "TradeIntent",
    "TradeResult",
    "assert_can_execute",
    "entry_window",
    "expected_schedule",
    "settlement_wait_seconds",
]
