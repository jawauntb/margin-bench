"""Immutable records shared by the environment, policies and evaluator (SPEC 4, 6, 7).

Events, observations, actions and ledger entries are frozen dataclasses. Only the engine
owns mutable state (``environment/state.py``).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class Visibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    OBSERVABLE_AFTER_EVENT = "OBSERVABLE_AFTER_EVENT"
    LATENT = "LATENT"
    EVALUATOR_ONLY = "EVALUATOR_ONLY"


POLICY_VISIBLE = frozenset({Visibility.PUBLIC, Visibility.OBSERVABLE_AFTER_EVENT})


class Stage(str, enum.Enum):
    NEW = "NEW"
    INFO_WAIT = "INFO_WAIT"
    DISPATCH_READY = "DISPATCH_READY"
    DEFER_WAIT = "DEFER_WAIT"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    WORK_REPORTED = "WORK_REPORTED"
    VERIFY_PENDING = "VERIFY_PENDING"
    VERIFIED_OK = "VERIFIED_OK"
    VERIFIED_FAIL = "VERIFIED_FAIL"
    CLOSED = "CLOSED"


DECISION_STAGES = frozenset(
    {Stage.NEW, Stage.DISPATCH_READY, Stage.WORK_REPORTED, Stage.VERIFIED_OK, Stage.VERIFIED_FAIL}
)


class ActionType(str, enum.Enum):
    TRIAGE = "triage"
    REQUEST_INFO = "request_info"
    DISPATCH = "dispatch"
    ESCALATE = "escalate"
    DEFER = "defer"
    CLOSE = "close"
    VERIFY = "verify"
    REDISPATCH = "redispatch"


ACTION_ORDER = {
    ActionType.TRIAGE: 0,
    ActionType.REQUEST_INFO: 1,
    ActionType.CLOSE: 2,
    ActionType.VERIFY: 3,
    ActionType.DISPATCH: 4,
    ActionType.REDISPATCH: 5,
    ActionType.ESCALATE: 6,
    ActionType.DEFER: 7,
}

DISPATCH_LIKE = frozenset({ActionType.DISPATCH, ActionType.REDISPATCH, ActionType.ESCALATE})


class Principal(str, enum.Enum):
    OPERATOR = "OPERATOR"
    OWNER = "OWNER"
    TENANT = "TENANT"
    CONTRACTOR = "CONTRACTOR"
    THIRD_PARTY = "THIRD_PARTY"


class EntryStatus(str, enum.Enum):
    REALIZED = "REALIZED"
    ACCRUED = "ACCRUED"


class IllegalActionError(RuntimeError):
    """A policy returned an action that is not in the legal set (SPEC 7.3)."""


@dataclass(frozen=True)
class Action:
    request_id: str
    stage: Stage
    type: ActionType
    contractor: Optional[str] = None
    tick: int = 0
    reason_code: str = ""
    estimated_value: Optional[float] = None
    estimated_risk: Optional[float] = None
    action_id: str = ""

    def sort_key(self) -> tuple[int, str]:
        return (ACTION_ORDER[self.type], self.contractor or "")

    def identity(self) -> tuple[str, str, str, str, int]:
        return (self.request_id, self.stage.value, self.type.value, self.contractor or "", self.tick)

    def label(self) -> str:
        return self.type.value if self.contractor is None else f"{self.type.value}({self.contractor})"


@dataclass(frozen=True)
class Event:
    """Immutable engine event. ``data`` is a tuple of sorted (key, value) pairs."""

    event_id: int
    tick: int
    priority: int
    type: str
    request_id: Optional[str] = None
    property_id: Optional[str] = None
    data: tuple[tuple[str, Any], ...] = ()

    @property
    def payload(self) -> dict[str, Any]:
        return dict(self.data)

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tick": self.tick,
            "priority": self.priority,
            "type": self.type,
            "request_id": self.request_id,
            "property_id": self.property_id,
            "data": dict(self.data),
        }


def make_data(**kw: Any) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(kw.items()))


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: int
    run_id: str
    event_id: int
    tick: int
    principal: Principal
    category: str
    amount_cents: int
    contract_id: str
    request_id: Optional[str] = None
    action_id: Optional[str] = None
    status: EntryStatus = EntryStatus.REALIZED
    reversal_of: Optional[int] = None

    def to_record(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "run_id": self.run_id,
            "event_id": self.event_id,
            "tick": self.tick,
            "principal": self.principal.value,
            "category": self.category,
            "amount_cents": self.amount_cents,
            "contract_id": self.contract_id,
            "request_id": self.request_id,
            "action_id": self.action_id,
            "status": self.status.value,
            "reversal_of": self.reversal_of,
        }


# ----------------------------------------------------------------------------------------
# Policy observation schema (built only by environment/observations.py's allowlist)
# ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AttemptView:
    attempt_index: int  # number of prior jobs when this job was dispatched (j)
    contractor: str
    escalated: bool
    dispatch_tick: int
    start_tick: Optional[int]
    reported_severity_at_dispatch: str
    report: Optional[str]  # "complete" / "needs_return" once reported
    verify_result: Optional[str]  # "ok" / "fail" when verified
    invoice_cents: Optional[int]


@dataclass(frozen=True)
class RequestView:
    request_id: str
    property_id: str
    tenant_id: str
    category: str
    arrival_tick: int
    reported_severity: str
    stage: Stage
    attempt_index: int
    observed_failure_count: int
    defer_count: int
    info_requested: bool
    sla_tier: Optional[str]
    sla_deadline_tick: Optional[int]
    sla_breached: bool
    first_start_tick: Optional[int]
    first_closure_tick: Optional[int]
    last_close_unverified: bool
    callback_count: int
    reopened_by_callback: bool
    had_severe_loss: bool
    attempts: tuple[AttemptView, ...]


@dataclass(frozen=True)
class ContractorView:
    contractor_id: str
    price_multiplier: float
    eligible: tuple[str, ...]
    speed: float
    capacity: int
    queue_length: int
    earliest_start_tick: Optional[int]  # for a dispatch of this request now, from the public schedule
    escalation_start_tick: int
    observed_ok: int
    observed_fail: int
    observed_callbacks: int


@dataclass(frozen=True)
class PropertyView:
    property_id: str
    owner_id: str
    contract_id: str
    unit_count: int
    condition_grade: float
    contract_status: str
    fee_per_day: float
    cb90: float  # owner-visible callbacks per unit, trailing 90 days
    br90: float  # SLA breaches, trailing 90 days
    sl365: float  # severe losses, trailing 365 days
    oc90: float  # owner repair spend per unit / $100, trailing 90 days


@dataclass(frozen=True)
class Observation:
    tick: int
    day: int
    request: RequestView
    property: PropertyView
    contractors: tuple[ContractorView, ...]
    tenant_complaint_count: int
    mc_seed: int  # runner-supplied Monte Carlo seed for this decision (SPEC 11; DECISIONS D-12)


@dataclass(frozen=True)
class ObservableEvent:
    tick: int
    type: str
    request_id: Optional[str]
    property_id: Optional[str]
    data: tuple[tuple[str, Any], ...] = field(default=())
