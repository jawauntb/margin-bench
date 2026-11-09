"""Trace validation: every request's event sequence must follow the SPEC 7.1 transition
table exactly. Any violation makes the run INVALID."""

from __future__ import annotations

from typing import Any, Iterable

from marginbench.schemas import Event

ACTION_TRANSITIONS: dict[tuple[str, str], str] = {
    ("NEW", "triage"): "DISPATCH_READY",
    ("NEW", "request_info"): "INFO_WAIT",
    ("DISPATCH_READY", "dispatch"): "QUEUED",
    ("DISPATCH_READY", "escalate"): "QUEUED",
    ("DISPATCH_READY", "defer"): "DEFER_WAIT",
    ("WORK_REPORTED", "close"): "CLOSED",
    ("WORK_REPORTED", "verify"): "VERIFY_PENDING",
    ("WORK_REPORTED", "redispatch"): "QUEUED",
    ("WORK_REPORTED", "escalate"): "QUEUED",
    ("VERIFIED_OK", "close"): "CLOSED",
    ("VERIFIED_FAIL", "redispatch"): "QUEUED",
    ("VERIFIED_FAIL", "escalate"): "QUEUED",
}

EVENT_TRANSITIONS: dict[tuple[str, str], str] = {
    ("INFO_WAIT", "INFO_ARRIVES"): "DISPATCH_READY",
    ("DEFER_WAIT", "DEFER_ELAPSES"): "DISPATCH_READY",
    ("QUEUED", "WORK_START"): "IN_PROGRESS",
    ("IN_PROGRESS", "WORK_COMPLETE"): "WORK_REPORTED",
    ("CLOSED", "CALLBACK"): "DISPATCH_READY",
}

NEUTRAL = {"SLA_BREACH", "SEVERE_LOSS"}


def validate_transitions(events: Iterable[Event]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    stage: dict[str, str] = {}
    last_report: dict[str, str] = {}
    done: set[str] = set()
    for ev in events:
        rid = ev.request_id
        if rid is None or ev.type in NEUTRAL or ev.type == "OPPORTUNITY_UNSERVED":
            continue
        if rid in done:
            errors.append({"check": "event_after_handover", "request_id": rid, "event_id": ev.event_id})
            continue
        if ev.type == "ARRIVAL":
            if rid in stage:
                errors.append({"check": "duplicate_arrival", "request_id": rid})
            stage[rid] = "NEW"
            continue
        cur = stage.get(rid)
        if cur is None:
            errors.append({"check": "event_before_arrival", "request_id": rid, "event_id": ev.event_id})
            continue
        if ev.type == "HANDOVER":
            done.add(rid)
            continue
        p = ev.payload
        if ev.type == "ACTION":
            t = p["action_type"]
            if p["stage"] != cur:
                errors.append({"check": "action_stage_mismatch", "request_id": rid, "event_id": ev.event_id,
                               "stage": cur, "action_stage": p["stage"]})
            nxt = ACTION_TRANSITIONS.get((cur, t))
            if nxt is None:
                errors.append({"check": "illegal_transition", "request_id": rid, "from": cur, "action": t})
                continue
            if cur == "WORK_REPORTED" and t in ("close", "verify") and last_report.get(rid) != "complete":
                errors.append({"check": "close_or_verify_without_complete_report", "request_id": rid})
            stage[rid] = nxt
        elif ev.type == "VERIFY_RESULT":
            if cur != "VERIFY_PENDING":
                errors.append({"check": "illegal_transition", "request_id": rid, "from": cur, "event": ev.type})
            stage[rid] = "VERIFIED_OK" if p["result"] == "ok" else "VERIFIED_FAIL"
        else:
            nxt = EVENT_TRANSITIONS.get((cur, ev.type))
            if nxt is None:
                errors.append({"check": "illegal_transition", "request_id": rid, "from": cur, "event": ev.type})
                continue
            if ev.type == "WORK_COMPLETE":
                last_report[rid] = p["report"]
            stage[rid] = nxt
    return errors
