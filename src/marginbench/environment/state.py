"""Mutable engine state. Every field carries exactly one visibility class (SPEC 4).

Only the engine mutates these objects. Policies never receive them: they receive
``schemas.Observation`` built by the allowlist serializer in ``observations.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Optional

from marginbench.schemas import Stage, Visibility

P = Visibility.PUBLIC
O = Visibility.OBSERVABLE_AFTER_EVENT
L = Visibility.LATENT
E = Visibility.EVALUATOR_ONLY


def vf(vis: Visibility, default: Any = None, factory: Any = None) -> Any:
    if factory is not None:
        return field(default_factory=factory, metadata={"vis": vis})
    return field(default=default, metadata={"vis": vis})


def visibility_map(cls: type) -> dict[str, Visibility]:
    out: dict[str, Visibility] = {}
    for f in fields(cls):
        vis = f.metadata.get("vis")
        if not isinstance(vis, Visibility):
            raise TypeError(f"{cls.__name__}.{f.name} has no visibility class")
        out[f.name] = vis
    return out


@dataclass
class PropertyState:
    property_id: str = vf(P, "")
    owner_id: str = vf(P, "")
    contract_id: str = vf(P, "")
    unit_count: int = vf(P, 10)
    risk: float = vf(L, 1.0)
    condition: float = vf(L, 0.7)
    condition_obs: float = vf(P, 0.7)
    # owner-visible event logs (day, weight) used for trailing retention features
    callback_log: list[tuple[int, float]] = vf(O, factory=list)
    breach_log: list[tuple[int, float]] = vf(O, factory=list)
    loss_log: list[tuple[int, float]] = vf(O, factory=list)
    spend_log: list[tuple[int, float]] = vf(O, factory=list)


@dataclass
class TenantState:
    tenant_id: str = vf(P, "")
    unit_id: str = vf(P, "")
    property_id: str = vf(P, "")
    report_propensity: float = vf(L, 0.8)
    complaint_count: int = vf(O, 0)


@dataclass
class ContractorState:
    contractor_id: str = vf(P, "")
    price_multiplier: float = vf(P, 1.0)
    eligible: tuple[str, ...] = vf(P, ())
    speed: float = vf(P, 1.0)
    capacity: int = vf(P, 1)  # effective daily capacity (after multiplier); 0 = unlimited
    schedule: dict[int, int] = vf(P, factory=dict)  # day -> slots used (public schedule)
    pending_starts: list[int] = vf(P, factory=list)  # start ticks of scheduled jobs (queue)
    logit_success: float = vf(L, 0.0)
    category_offsets: dict[str, float] = vf(L, factory=dict)
    observed_ok: int = vf(O, 0)
    observed_fail: int = vf(O, 0)
    observed_callbacks: int = vf(O, 0)


@dataclass
class ContractState:
    contract_id: str = vf(P, "")
    property_id: str = vf(P, "")
    annual_fee_cents: int = vf(P, 0)
    status: str = vf(O, "ACTIVE")  # ACTIVE / NOTICE / TERMINATED
    notice_day: Optional[int] = vf(O, None)
    effective_day: Optional[int] = vf(O, None)
    booked_fee_cents: int = vf(E, 0)
    last_hazard: float = vf(L, 0.0)


@dataclass
class AttemptRecord:
    attempt_index: int = vf(O, 0)
    contractor: str = vf(O, "")
    escalated: bool = vf(O, False)
    dispatch_tick: int = vf(O, 0)
    start_tick: Optional[int] = vf(O, None)
    reported_severity_at_dispatch: str = vf(O, "minor")
    report: Optional[str] = vf(O, None)
    verify_result: Optional[str] = vf(O, None)
    invoice_cents: Optional[int] = vf(O, None)
    success: Optional[bool] = vf(E, None)


@dataclass
class RequestState:
    request_id: str = vf(P, "")
    property_id: str = vf(P, "")
    tenant_id: str = vf(P, "")
    category: str = vf(P, "general")
    arrival_tick: int = vf(P, 0)
    reported_severity: str = vf(P, "minor")
    true_severity: str = vf(L, "minor")
    physical_resolved: bool = vf(L, False)
    stage: Stage = vf(O, Stage.NEW)
    attempt_index: int = vf(O, 0)
    observed_failure_count: int = vf(O, 0)
    defer_count: int = vf(O, 0)
    info_requested: bool = vf(O, False)
    sla_tier: Optional[str] = vf(O, None)
    sla_deadline_tick: Optional[int] = vf(O, None)
    sla_breached: bool = vf(O, False)
    first_start_tick: Optional[int] = vf(O, None)
    first_closure_tick: Optional[int] = vf(O, None)
    last_close_unverified: bool = vf(O, False)
    callback_count: int = vf(O, 0)
    reopened_by_callback: bool = vf(O, False)
    had_severe_loss: bool = vf(O, False)
    attempts: list[AttemptRecord] = vf(O, factory=list)
    decision_index: int = vf(O, 0)  # decisions taken on this request so far
    verification_index: int = vf(O, 0)
    failure_episode_index: int = vf(E, 0)
    benign_drawn: bool = vf(E, False)
    pending_true_callback_tick: Optional[int] = vf(E, None)
    unreported_failure: bool = vf(E, False)
    severe_loss_cents: int = vf(E, 0)
    handed_over: bool = vf(E, False)
    cohort: bool = vf(E, False)
    resolved_tick: Optional[int] = vf(E, None)
    first_verified_ok_tick: Optional[int] = vf(E, None)


STATE_CLASSES = (PropertyState, TenantState, ContractorState, ContractState, AttemptRecord, RequestState)


def check_visibility_registry() -> None:
    for cls in STATE_CLASSES:
        visibility_map(cls)
