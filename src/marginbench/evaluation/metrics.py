"""Per-run metrics (SPEC 8, 16). The proxy G is ``proxy_v1`` and is frozen.

Undefined values are ``None`` and carry a reason in ``undefined``; they are never 0.
"""

from __future__ import annotations

import statistics as st
from typing import Any, Optional

from marginbench.config import Config
from marginbench.economics.ledger import PROXY_OPEX_CATEGORIES
from marginbench.economics.valuation import cumulative_discounted, discounted_contribution_cents
from marginbench.schemas import Principal

DAY = 1440


def cutoff_tick(cfg: Config) -> int:
    """End of day (decision end + 14): events with tick < cutoff_tick are 'by the cutoff'."""
    return (cfg.time.proxy_cutoff_day + 1) * DAY


def closure_target_ticks(cfg: Config, tier: str) -> int:
    return cfg.proxy.closure_target_days[tier] * DAY


def proxy_value(cr: Optional[float], opex_dollars: float, n: int, cfg: Config) -> Optional[float]:
    """G = CR - 0.5 * (OPEX / N) / 25. N = 0 -> None (UNDEFINED, never 0)."""
    if n == 0 or cr is None:
        return None
    return cr - cfg.proxy.opex_weight * (opex_dollars / n) / cfg.proxy.opex_scale


def _ratio(num: float, den: float) -> Optional[float]:
    return None if den == 0 else num / den


def compute_metrics(out: Any, cfg: Config, horizon_days: int) -> dict[str, Any]:
    cut = cutoff_tick(cfg)
    d0 = cfg.time.d0
    d_end = horizon_days - 1
    reqs = out.requests
    cohort = sorted(r for r, q in reqs.items() if q.cohort)
    n = len(cohort)
    undefined: dict[str, str] = {}

    # --- proxy -----------------------------------------------------------------------------
    closed_in_target = 0
    for rid in cohort:
        q = reqs[rid]
        tier = q.sla_tier or q.reported_severity
        if q.first_closure_tick is not None and q.first_closure_tick < cut and \
                q.first_closure_tick - q.arrival_tick <= closure_target_ticks(cfg, tier):
            closed_in_target += 1
    cohort_set = set(cohort)
    opex_cents = 0
    for e in out.ledger.entries:
        if e.principal == Principal.OPERATOR and e.category in PROXY_OPEX_CATEGORIES and \
                e.request_id in cohort_set and e.tick < cut:
            opex_cents += -e.amount_cents
    opex = opex_cents / 100.0
    cr = _ratio(closed_in_target, n)
    G = proxy_value(cr, opex, n, cfg)
    if n == 0:
        for k in ("G", "closure_rate", "opex_per_request"):
            undefined[k] = "empty cohort (N = 0)"

    # --- operational ----------------------------------------------------------------------
    verified = sum(1 for r in cohort if reqs[r].first_verified_ok_tick is not None and reqs[r].first_verified_ok_tick < cut)
    true_res = sum(1 for r in cohort if reqs[r].resolved_tick is not None and reqs[r].resolved_tick < cut)
    cb_cohort = sum(1 for r in cohort for t in out.callback_ticks.get(r, []) if t < cut)
    reopened = sum(1 for r in cohort if any(t < cut for t in out.callback_ticks.get(r, [])))
    completed_attempts = 0
    for r in cohort:
        for a in reqs[r].attempts:
            if a.report is not None and a.start_tick is not None:
                completed_attempts += 1  # report exists -> completion; refined below by tick
    # completion ticks come from events
    comp_by_req: dict[str, int] = {}
    for ev in out.events:
        if ev.type == "WORK_COMPLETE" and ev.request_id in cohort_set and ev.tick < cut:
            comp_by_req[ev.request_id] = comp_by_req.get(ev.request_id, 0) + 1
    completed_attempts = sum(comp_by_req.values())
    t_close = [(reqs[r].first_closure_tick - reqs[r].arrival_tick) / DAY for r in cohort
               if reqs[r].first_closure_tick is not None and reqs[r].first_closure_tick < cut]
    t_ver = [(reqs[r].first_verified_ok_tick - reqs[r].arrival_tick) / DAY for r in cohort
             if reqs[r].first_verified_ok_tick is not None and reqs[r].first_verified_ok_tick < cut]
    acts_cohort = [a for a in out.action_records if a["request_id"] in cohort_set and a["tick"] < cut]
    n_disp = sum(1 for a in acts_cohort if a["type"] in ("dispatch", "redispatch", "escalate"))
    n_esc = sum(1 for a in acts_cohort if a["type"] == "escalate")
    n_ver = sum(1 for a in acts_cohort if a["type"] == "verify")
    n_close = sum(1 for a in acts_cohort if a["type"] == "close")

    intervals = open_intervals(out, horizon_days * DAY)
    open_at_cut = [(rid, s) for rid, iv in intervals.items() for (s, e) in iv if s < cut <= e]
    backlog_age = [(cut - reqs[rid].arrival_tick) / DAY for rid, _ in open_at_cut]

    # contractor utilization in the decision window
    util: dict[str, Optional[float]] = {}
    w0, w1 = cfg.time.d0 * DAY, (cfg.time.decision_end_day + 1) * DAY
    starts: dict[str, int] = {}
    for ev in out.events:
        if ev.type == "WORK_START" and w0 <= ev.tick < w1:
            c = ev.payload["contractor"]
            starts[c] = starts.get(c, 0) + 1
    for cid, c in sorted(out.contractors.items()):
        util[cid] = None if c.capacity <= 0 else starts.get(cid, 0) / (c.capacity * cfg.time.decision_days)

    # --- economic ---------------------------------------------------------------------------
    daily = out.ledger.operator_daily(horizon_days)
    J_cents = discounted_contribution_cents(daily, d0, d_end, cfg.time.delta)
    nominal = sum(daily[d0 : d_end + 1])
    op_cat: dict[str, int] = {}
    own_cat: dict[str, int] = {}
    loss_by_principal: dict[str, int] = {"OPERATOR": 0, "OWNER": 0}
    w_lo = d0 * DAY
    for e in out.ledger.entries:
        if e.tick < w_lo:
            continue
        if e.principal == Principal.OPERATOR:
            op_cat[e.category] = op_cat.get(e.category, 0) + e.amount_cents
        elif e.principal == Principal.OWNER:
            own_cat[e.category] = own_cat.get(e.category, 0) + e.amount_cents
        if e.category == "severe_loss":
            loss_by_principal[e.principal.value] += e.amount_cents
    n_loss = sum(1 for ev in out.events if ev.type == "SEVERE_LOSS" and ev.tick >= w_lo)
    n_breach = sum(1 for ev in out.events if ev.type == "SLA_BREACH" and ev.tick >= w_lo)
    n_cb_all = sum(1 for ev in out.events if ev.type == "CALLBACK" and ev.tick >= w_lo)
    lost = sum(1 for k in out.contracts.values() if k.status in ("NOTICE", "TERMINATED"))

    if completed_attempts == 0:
        undefined["callback_rate_per_completed_attempt"] = "no completed attempts"
    if not t_close:
        undefined["time_to_first_closure_days"] = "no closures by cutoff"
    if not t_ver:
        undefined["time_to_verified_resolution_days"] = "no verified resolutions by cutoff"
    if not open_at_cut:
        undefined["backlog_age_days"] = "no open requests at cutoff"
    if n_disp == 0:
        undefined["escalation_rate"] = "no dispatch-like actions"
    if n_close == 0:
        undefined["verification_rate"] = "no closes"

    return {
        "N": n,
        "G": G,
        "closure_rate": cr,
        "closed_in_target": closed_in_target,
        "opex_dollars": opex,
        "opex_per_request": _ratio(opex, n),
        "J_dollars": J_cents / 100.0,
        "J_cents": J_cents,
        "nominal_contribution_dollars": nominal / 100.0,
        "verified_resolution_rate": _ratio(verified, n),
        "true_resolution_rate": _ratio(true_res, n),
        "callback_rate_per_completed_attempt": _ratio(cb_cohort, completed_attempts),
        "reopen_rate": _ratio(reopened, n),
        "time_to_first_closure_days_mean": st.fmean(t_close) if t_close else None,
        "time_to_first_closure_days_median": st.median(t_close) if t_close else None,
        "time_to_verified_resolution_days_mean": st.fmean(t_ver) if t_ver else None,
        "time_to_verified_resolution_days_median": st.median(t_ver) if t_ver else None,
        "backlog_at_cutoff": len(open_at_cut),
        "backlog_age_days": st.fmean(backlog_age) if backlog_age else None,
        "escalation_rate": _ratio(n_esc, n_disp),
        "verification_rate": _ratio(n_ver, n_close),
        "contractor_utilization": util,
        "unreported_failure_count": out.boundary["unreported_failures"],
        "operator_by_category_dollars": {k: v / 100.0 for k, v in sorted(op_cat.items())},
        "owner_by_category_dollars": {k: v / 100.0 for k, v in sorted(own_cat.items())},
        "losses_by_principal_dollars": {k: v / 100.0 for k, v in loss_by_principal.items()},
        "severe_loss_count": n_loss,
        "sla_breach_count": n_breach,
        "callback_count": n_cb_all,
        "contracts_lost": lost,
        "undefined": undefined,
    }


def open_intervals(out: Any, end_tick: int) -> dict[str, list[tuple[int, int]]]:
    """Open (administratively not closed) intervals per request, from the event log."""
    opened: dict[str, int] = {}
    iv: dict[str, list[tuple[int, int]]] = {}
    for ev in out.events:
        rid = ev.request_id
        if ev.type == "ARRIVAL":
            opened[rid] = ev.tick
        elif ev.type == "CALLBACK":
            opened[rid] = ev.tick
        elif ev.type == "ACTION" and ev.payload["action_type"] == "close":
            s = opened.pop(rid, None)
            if s is not None:
                iv.setdefault(rid, []).append((s, ev.tick))
        elif ev.type == "HANDOVER":
            s = opened.pop(rid, None)
            if s is not None:
                iv.setdefault(rid, []).append((s, ev.tick))
    for rid, s in opened.items():
        iv.setdefault(rid, []).append((s, end_tick))
    return iv


def daily_series(out: Any, cfg: Config, horizon_days: int) -> dict[str, list[float]]:
    """Time series for charts: backlog at end of day, callbacks per day, cumulative discounted J."""
    end = horizon_days * DAY
    intervals = open_intervals(out, end)
    backlog = [0] * horizon_days
    for ivs in intervals.values():
        for s, e in ivs:
            d_s = s // DAY
            d_e = min(horizon_days - 1, (e - 1) // DAY) if e > s else d_s - 1
            for d in range(d_s, d_e + 1):
                if s <= (d + 1) * DAY - 1 < e:
                    backlog[d] += 1
    cbs = [0] * horizon_days
    for ev in out.events:
        if ev.type == "CALLBACK":
            cbs[ev.tick // DAY] += 1
    daily = out.ledger.operator_daily(horizon_days)
    cum = cumulative_discounted(daily, cfg.time.d0, horizon_days - 1, cfg.time.delta)
    return {"backlog": [float(x) for x in backlog], "callbacks": [float(x) for x in cbs],
            "cum_discounted_dollars": [x / 100.0 for x in cum]}
