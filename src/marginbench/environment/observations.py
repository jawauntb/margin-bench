"""Allowlist serializer for policy observations (SPEC 4).

Each observation field is listed below with the state fields it is derived from. Every
source field must be PUBLIC or OBSERVABLE_AFTER_EVENT. Fields not in the allowlist are
never read and never forwarded; ``validate_observation_record`` rejects unknown keys.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional

from marginbench.environment.state import (
    AttemptRecord,
    ContractorState,
    ContractState,
    PropertyState,
    RequestState,
    TenantState,
    visibility_map,
)
from marginbench.hashing import to_jsonable
from marginbench.schemas import (
    POLICY_VISIBLE,
    AttemptView,
    ContractorView,
    ObservableEvent,
    Observation,
    PropertyView,
    RequestView,
)

# view field -> (state class, source fields)
ALLOWLIST: dict[type, dict[str, tuple[type, tuple[str, ...]]]] = {
    AttemptView: {
        "attempt_index": (AttemptRecord, ("attempt_index",)),
        "contractor": (AttemptRecord, ("contractor",)),
        "escalated": (AttemptRecord, ("escalated",)),
        "dispatch_tick": (AttemptRecord, ("dispatch_tick",)),
        "start_tick": (AttemptRecord, ("start_tick",)),
        "reported_severity_at_dispatch": (AttemptRecord, ("reported_severity_at_dispatch",)),
        "report": (AttemptRecord, ("report",)),
        "verify_result": (AttemptRecord, ("verify_result",)),
        "invoice_cents": (AttemptRecord, ("invoice_cents",)),
        "closed_tick": (AttemptRecord, ("closed_tick",)),
        "callback_tick": (AttemptRecord, ("callback_tick",)),
    },
    RequestView: {
        "request_id": (RequestState, ("request_id",)),
        "property_id": (RequestState, ("property_id",)),
        "tenant_id": (RequestState, ("tenant_id",)),
        "category": (RequestState, ("category",)),
        "arrival_tick": (RequestState, ("arrival_tick",)),
        "reported_severity": (RequestState, ("reported_severity",)),
        "stage": (RequestState, ("stage",)),
        "attempt_index": (RequestState, ("attempt_index",)),
        "observed_failure_count": (RequestState, ("observed_failure_count",)),
        "defer_count": (RequestState, ("defer_count",)),
        "info_requested": (RequestState, ("info_requested",)),
        "sla_tier": (RequestState, ("sla_tier",)),
        "sla_deadline_tick": (RequestState, ("sla_deadline_tick",)),
        "sla_breached": (RequestState, ("sla_breached",)),
        "first_start_tick": (RequestState, ("first_start_tick",)),
        "first_closure_tick": (RequestState, ("first_closure_tick",)),
        "last_close_unverified": (RequestState, ("last_close_unverified",)),
        "callback_count": (RequestState, ("callback_count",)),
        "reopened_by_callback": (RequestState, ("reopened_by_callback",)),
        "had_severe_loss": (RequestState, ("had_severe_loss",)),
        "attempts": (RequestState, ("attempts",)),
    },
    ContractorView: {
        "contractor_id": (ContractorState, ("contractor_id",)),
        "price_multiplier": (ContractorState, ("price_multiplier",)),
        "eligible": (ContractorState, ("eligible",)),
        "speed": (ContractorState, ("speed",)),
        "capacity": (ContractorState, ("capacity",)),
        "queue_length": (ContractorState, ("pending_starts",)),
        "earliest_start_tick": (ContractorState, ("schedule", "capacity", "speed", "eligible")),
        "escalation_start_tick": (ContractorState, ("speed",)),
        "observed_ok": (ContractorState, ("observed_ok",)),
        "observed_fail": (ContractorState, ("observed_fail",)),
        "observed_callbacks": (ContractorState, ("observed_callbacks",)),
    },
    PropertyView: {
        "property_id": (PropertyState, ("property_id",)),
        "owner_id": (PropertyState, ("owner_id",)),
        "contract_id": (PropertyState, ("contract_id",)),
        "unit_count": (PropertyState, ("unit_count",)),
        "condition_grade": (PropertyState, ("condition_obs",)),
        "contract_status": (ContractState, ("status",)),
        "fee_per_day": (ContractState, ("annual_fee_cents",)),
        "cb90": (PropertyState, ("callback_log", "unit_count")),
        "br90": (PropertyState, ("breach_log",)),
        "sl365": (PropertyState, ("loss_log",)),
        "oc90": (PropertyState, ("spend_log", "unit_count")),
    },
    Observation: {
        "tick": (RequestState, ()),
        "day": (RequestState, ()),
        "request": (RequestState, ()),
        "property": (PropertyState, ()),
        "contractors": (ContractorState, ()),
        "tenant_complaint_count": (TenantState, ("complaint_count",)),
        "mc_seed": (RequestState, ()),
    },
}

# Observable-event allowlist: event type -> payload keys that may reach policies.
OBSERVABLE_EVENT_KEYS: dict[str, tuple[str, ...]] = {
    "ARRIVAL": ("category", "reported_severity"),
    "ACTION": ("action_type", "contractor"),
    "WORK_START": ("contractor", "attempt_index"),
    "WORK_COMPLETE": ("contractor", "attempt_index", "report", "invoice_cents"),
    "VERIFY_RESULT": ("result",),
    "INFO_ARRIVES": ("reported_severity",),
    "DEFER_ELAPSES": (),
    "CALLBACK": (),
    "SLA_BREACH": ("tier",),
    "SEVERE_LOSS": ("owner_visible_amount_cents",),
    "TERMINATION_NOTICE": ("effective_day",),
    "CONTRACT_TERMINATED": (),
}


class ObservationLeakError(RuntimeError):
    pass


def validate_allowlist() -> None:
    """Fails if any observation field is not allowlisted or draws on a non-visible field."""
    for view, mapping in ALLOWLIST.items():
        names = {f.name for f in dataclasses.fields(view)}
        if names != set(mapping):
            raise ObservationLeakError(f"{view.__name__}: fields {sorted(names ^ set(mapping))} not allowlisted")
        for vf_name, (cls, sources) in mapping.items():
            vis = visibility_map(cls)
            for s in sources:
                if s not in vis:
                    raise ObservationLeakError(f"{view.__name__}.{vf_name}: unknown source {cls.__name__}.{s}")
                if vis[s] not in POLICY_VISIBLE:
                    raise ObservationLeakError(f"{view.__name__}.{vf_name}: source {cls.__name__}.{s} is {vis[s].value}")


def attempt_view(a: AttemptRecord) -> AttemptView:
    return AttemptView(
        attempt_index=a.attempt_index,
        contractor=a.contractor,
        escalated=a.escalated,
        dispatch_tick=a.dispatch_tick,
        start_tick=a.start_tick,
        reported_severity_at_dispatch=a.reported_severity_at_dispatch,
        report=a.report,
        verify_result=a.verify_result,
        invoice_cents=a.invoice_cents,
        closed_tick=a.closed_tick,
        callback_tick=a.callback_tick,
    )


def request_view(r: RequestState) -> RequestView:
    return RequestView(
        request_id=r.request_id,
        property_id=r.property_id,
        tenant_id=r.tenant_id,
        category=r.category,
        arrival_tick=r.arrival_tick,
        reported_severity=r.reported_severity,
        stage=r.stage,
        attempt_index=r.attempt_index,
        observed_failure_count=r.observed_failure_count,
        defer_count=r.defer_count,
        info_requested=r.info_requested,
        sla_tier=r.sla_tier,
        sla_deadline_tick=r.sla_deadline_tick,
        sla_breached=r.sla_breached,
        first_start_tick=r.first_start_tick,
        first_closure_tick=r.first_closure_tick,
        last_close_unverified=r.last_close_unverified,
        callback_count=r.callback_count,
        reopened_by_callback=r.reopened_by_callback,
        had_severe_loss=r.had_severe_loss,
        attempts=tuple(attempt_view(a) for a in r.attempts),
    )


def contractor_view(c: ContractorState, tick: int, earliest_start: Optional[int], escalation_start: int) -> ContractorView:
    return ContractorView(
        contractor_id=c.contractor_id,
        price_multiplier=c.price_multiplier,
        eligible=tuple(c.eligible),
        speed=c.speed,
        capacity=c.capacity,
        queue_length=sum(1 for s in c.pending_starts if s > tick),
        earliest_start_tick=earliest_start,
        escalation_start_tick=escalation_start,
        observed_ok=c.observed_ok,
        observed_fail=c.observed_fail,
        observed_callbacks=c.observed_callbacks,
    )


def property_view(p: PropertyState, k: ContractState, feats: dict[str, float]) -> PropertyView:
    return PropertyView(
        property_id=p.property_id,
        owner_id=p.owner_id,
        contract_id=p.contract_id,
        unit_count=p.unit_count,
        condition_grade=p.condition_obs,
        contract_status=k.status,
        fee_per_day=k.annual_fee_cents / 365.0 / 100.0,
        cb90=feats["cb"],
        br90=feats["br"],
        sl365=feats["sl"],
        oc90=feats["oc"],
    )


def observable_event(ev_type: str, tick: int, request_id: Optional[str], property_id: Optional[str],
                     payload: dict[str, Any]) -> Optional[ObservableEvent]:
    keys = OBSERVABLE_EVENT_KEYS.get(ev_type)
    if keys is None:
        return None
    data = tuple(sorted((k, payload[k]) for k in keys if k in payload))
    return ObservableEvent(tick=tick, type=ev_type, request_id=request_id, property_id=property_id, data=data)


def observation_record(obs: Observation) -> dict[str, Any]:
    rec = to_jsonable(obs)
    validate_observation_record(rec)
    return rec


def validate_observation_record(rec: dict[str, Any]) -> None:
    def check(view: type, d: dict[str, Any]) -> None:
        allowed = set(ALLOWLIST[view])
        extra = set(d) - allowed
        if extra:
            raise ObservationLeakError(f"{view.__name__}: unknown fields {sorted(extra)}")

    check(Observation, rec)
    check(RequestView, rec["request"])
    for a in rec["request"]["attempts"]:
        check(AttemptView, a)
    check(PropertyView, rec["property"])
    for c in rec["contractors"]:
        check(ContractorView, c)
