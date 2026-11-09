"""Ledger reconciliation and replay (SPEC 6.5, 18.5).

``replay_entries`` rebuilds the ledger from the event log and the config alone, without
touching engine state. ``reconcile`` compares it with the engine's ledger and runs the
structural checks. Any failure makes the run INVALID.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from marginbench.config import Config
from marginbench.economics.contracts import annual_fee_cents, daily_fee_cents
from marginbench.economics.ledger import CATEGORY_RULES
from marginbench.schemas import EntryStatus, Event, LedgerEntry, Principal

ALLOWED_EVENT_TYPES: dict[str, frozenset[str]] = {
    "fee_revenue": frozenset({"DAY_START"}),
    "dispatch_expense": frozenset({"ACTION"}),
    "verification_expense": frozenset({"ACTION"}),
    "escalation_expense": frozenset({"ACTION"}),
    "info_expense": frozenset({"ACTION"}),
    "callback_expense": frozenset({"CALLBACK"}),
    "sla_credit_paid": frozenset({"SLA_BREACH"}),
    "sla_credit_received": frozenset({"SLA_BREACH"}),
    "repair_invoice": frozenset({"WORK_COMPLETE"}),
    "severe_loss": frozenset({"SEVERE_LOSS"}),
}


def _c(d: float) -> int:
    return int(round(d * 100))


def replay_entries(events: Iterable[Event], cfg: Config, run_id: str, contract_ids: list[str],
                   contract_property: dict[str, str]) -> list[LedgerEntry]:
    events = list(events)
    term_day: dict[str, int] = {}
    for ev in events:
        if ev.type == "CONTRACT_TERMINATED":
            p = ev.payload
            term_day[p["contract_id"]] = int(p["day"])
    prop_contract = {v: k for k, v in contract_property.items()}
    annual = {k: annual_fee_cents(cfg.fees.per_unit_month, cfg.portfolio.units_per_property) for k in contract_ids}
    out: list[LedgerEntry] = []

    def add(ev: Event, principal: Principal, category: str, cents: int, kid: str, rid: Any = None,
            aid: Any = None, status: EntryStatus = EntryStatus.REALIZED) -> None:
        if cents == 0:
            return
        out.append(LedgerEntry(len(out), run_id, ev.event_id, ev.tick, principal, category, cents, kid, rid, aid, status))

    for ev in events:
        p = ev.payload
        kid = prop_contract.get(ev.property_id or "", "")
        rid = ev.request_id
        if ev.type == "DAY_START":
            d = int(p["day"])
            for k in sorted(contract_ids):
                if k in term_day and term_day[k] <= d:
                    continue
                add(ev, Principal.OPERATOR, "fee_revenue", daily_fee_cents(annual[k], d), k, status=EntryStatus.ACCRUED)
        elif ev.type == "ACTION":
            t = p["action_type"]
            aid = p["action_id"]
            if t in ("dispatch", "redispatch", "escalate"):
                add(ev, Principal.OPERATOR, "dispatch_expense", -_c(cfg.costs.dispatch), kid, rid, aid)
                if t == "escalate":
                    add(ev, Principal.OPERATOR, "escalation_expense", -_c(cfg.costs.escalation), kid, rid, aid)
            elif t == "verify":
                add(ev, Principal.OPERATOR, "verification_expense", -_c(cfg.verify.cost), kid, rid, aid)
            elif t == "request_info":
                add(ev, Principal.OPERATOR, "info_expense", -_c(cfg.costs.info), kid, rid, aid)
        elif ev.type == "WORK_COMPLETE":
            inv = int(round(cfg.invoice.base[p["category"]] * cfg.invoice.severity_multiplier[p["reported_severity_at_dispatch"]]
                            * p["price_multiplier"] * 100))
            add(ev, Principal.OWNER, "repair_invoice", -inv, kid, rid)
        elif ev.type == "CALLBACK":
            add(ev, Principal.OPERATOR, "callback_expense", -_c(cfg.costs.callback), kid, rid)
        elif ev.type == "SLA_BREACH":
            credit = _c(cfg.sla.credit[p["tier"]])
            add(ev, Principal.OPERATOR, "sla_credit_paid", -credit, kid, rid)
            add(ev, Principal.OWNER, "sla_credit_received", credit, kid, rid)
        elif ev.type == "SEVERE_LOSS":
            amount = int(p["amount_cents"])
            op = int(round(amount * cfg.loss.operator_negligence_share)) if p["negligent"] else 0
            add(ev, Principal.OWNER, "severe_loss", -(amount - op), kid, rid)
            add(ev, Principal.OPERATOR, "severe_loss", -op, kid, rid)
    return out


def _key(e: LedgerEntry) -> tuple[Any, ...]:
    return (e.event_id, e.tick, e.principal.value, e.category, e.amount_cents, e.contract_id, e.request_id, e.status.value)


def reconcile(events: list[Event], ledger_entries: list[LedgerEntry], cfg: Config, run_id: str,
              contract_ids: list[str], contract_property: dict[str, str], end_tick: int) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    by_id = {ev.event_id: ev for ev in events}
    # 1. duplicates
    ids = Counter(e.entry_id for e in ledger_entries)
    for k, n in ids.items():
        if n > 1:
            errors.append({"check": "duplicate_entry_id", "entry_id": k})
    keys = Counter((e.event_id, e.principal.value, e.category, e.contract_id) for e in ledger_entries)
    for k, n in keys.items():
        if n > 1:
            errors.append({"check": "duplicate_entry", "key": list(k)})
    term_day: dict[str, int] = {}
    for ev in events:
        if ev.type == "CONTRACT_TERMINATED":
            term_day[ev.payload["contract_id"]] = int(ev.payload["day"])
    for e in ledger_entries:
        ev = by_id.get(e.event_id)
        # 2. triggering event
        if ev is None or ev.type not in ALLOWED_EVENT_TYPES.get(e.category, frozenset()):
            errors.append({"check": "no_valid_trigger", "entry_id": e.entry_id, "category": e.category})
            continue
        if e.tick != ev.tick:
            errors.append({"check": "tick_mismatch", "entry_id": e.entry_id})
        # 3. payer attribution and sign
        allowed, sign = CATEGORY_RULES[e.category]
        if e.principal not in allowed or (e.amount_cents > 0) != (sign > 0) or e.amount_cents == 0:
            errors.append({"check": "payer_misattribution", "entry_id": e.entry_id, "category": e.category,
                           "principal": e.principal.value})
        # 4. fee accrual only on active contracts
        if e.category == "fee_revenue":
            d = int(ev.payload["day"])
            if e.contract_id in term_day and term_day[e.contract_id] <= d:
                errors.append({"check": "fee_on_inactive_contract", "entry_id": e.entry_id})
            if e.status != EntryStatus.ACCRUED:
                errors.append({"check": "fee_status", "entry_id": e.entry_id})
        # 5. pending items recorded as realized
        elif e.status != EntryStatus.REALIZED:
            errors.append({"check": "status", "entry_id": e.entry_id})
        if e.tick >= end_tick:
            errors.append({"check": "pending_recorded_as_realized", "entry_id": e.entry_id})
    # 6. event-derived recomputation
    replay = replay_entries(events, cfg, run_id, contract_ids, contract_property)
    a = Counter(_key(e) for e in ledger_entries)
    b = Counter(_key(e) for e in replay)
    if a != b:
        diff_a = list((a - b).elements())[:10]
        diff_b = list((b - a).elements())[:10]
        errors.append({"check": "event_derived_mismatch", "ledger_only": [list(x) for x in diff_a],
                       "replay_only": [list(x) for x in diff_b]})
    tot_l: Counter[str] = Counter()
    tot_r: Counter[str] = Counter()
    for e in ledger_entries:
        tot_l[e.principal.value] += e.amount_cents
    for e in replay:
        tot_r[e.principal.value] += e.amount_cents
    if dict(tot_l) != dict(tot_r):
        errors.append({"check": "principal_totals", "ledger": dict(tot_l), "replay": dict(tot_r)})
    return errors
