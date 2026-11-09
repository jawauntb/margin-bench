"""Event types, same-tick priorities and the event queue (SPEC 7.3: tick, priority, event_id)."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Optional

PRIORITY: dict[str, int] = {
    "DAY_START": 0,
    "WORK_START": 1,
    "SLA_CHECK": 2,
    "WORK_COMPLETE": 3,
    "VERIFY_RESULT": 4,
    "INFO_ARRIVES": 5,
    "DEFER_ELAPSES": 6,
    "CALLBACK": 7,
    "ARRIVAL": 8,
}

# Events emitted while handling another event take the priority of their cause.
EMITTED_TYPES = (
    "ACTION",
    "SLA_BREACH",
    "SEVERE_LOSS",
    "TERMINATION_NOTICE",
    "CONTRACT_TERMINATED",
    "HANDOVER",
    "OPPORTUNITY_UNSERVED",
)


@dataclass(order=True)
class Scheduled:
    tick: int
    priority: int
    event_id: int
    type: str = field(compare=False)
    request_id: Optional[str] = field(compare=False, default=None)
    data: dict[str, Any] = field(compare=False, default_factory=dict)


class EventQueue:
    def __init__(self) -> None:
        self._heap: list[Scheduled] = []

    def push(self, item: Scheduled) -> None:
        heapq.heappush(self._heap, item)

    def pop(self) -> Scheduled:
        return heapq.heappop(self._heap)

    def peek_tick(self) -> Optional[int]:
        return self._heap[0].tick if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)

    def pending(self) -> list[Scheduled]:
        return sorted(self._heap)
