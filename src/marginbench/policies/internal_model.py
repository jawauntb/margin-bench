"""Policy-side request-level Monte Carlo model (SPEC 9.1). Never imports ``environment/``.

For a candidate action, it simulates the future of this one request K times with M's
estimated parameters. Follow-on decisions inside a rollout use the fixed rollout rule:
P0's decision rule evaluated with M's estimates (no nested sampling). All candidate actions
at a decision consume the same uniform matrix (common random numbers).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from scipy import stats

from marginbench.config import PublicConfig
from marginbench.schemas import Action, ActionType, Observation, Stage

DAY = 1440.0
JOB_MINUTES = 120.0
R_UNIFORMS = 256

FEATURE_WEIGHT = {"cb": "per_unit", "br": "count", "sl": "count", "oc": "spend"}


@dataclass
class Outcome:
    score: float
    loss: bool
    breach: bool
    op_cash: float
    proxy_cost: float
    retention: float
    bonus: float


def belief_unresolved(obs: Observation, est: Any) -> float:
    """P(physically unresolved | observable history) from M (DECISIONS D-23)."""
    req = obs.request
    q = obs.property.condition_grade
    b = 1.0
    benign = float(est.params["callback"].get("benign_rate", 0.03))
    for a in req.attempts:
        if a.report is None:
            continue
        p = est.p_success(a.contractor, req.category, a.reported_severity_at_dispatch, a.attempt_index, q)
        b = est.posterior_unresolved(b, p, a.report, a.verify_result)
        if a.closed_tick is not None and a.callback_tick is not None:
            cu = a.verify_result is None
            pr = est.p_report(a.reported_severity_at_dispatch, cu)
            den = b * pr + (1.0 - b) * benign
            b = b * pr / den if den > 0 else b
    return min(1.0, max(0.0, b))


class RolloutContext:
    """Everything one decision's rollouts need, precomputed once per decision."""

    def __init__(self, obs: Observation, est: Any, pub: PublicConfig) -> None:
        self.obs = obs
        self.est = est
        self.pub = pub
        req = obs.request
        self.req = req
        self.k = req.category
        self.q = obs.property.condition_grade
        self.units = obs.property.unit_count
        self.fee_day = obs.property.fee_per_day
        self.cmap = {c.contractor_id: c for c in obs.contractors}
        self.eligible = [c.contractor_id for c in obs.contractors if self.k in c.eligible]
        self.b0 = belief_unresolved(obs, est)
        feats = {"cb": obs.property.cb90, "br": obs.property.br90, "sl": obs.property.sl365, "oc": obs.property.oc90}
        self.h_now = est.term_hazard(feats)
        self.beta = {f: est.term_beta(f) for f in ("cb", "br", "sl", "oc")}
        self.windows = pub.retention_windows
        self.share = pub.operator_negligence_share
        self.costs = pub.costs
        self.verify_cost = pub.verify_cost
        self.credit = pub.sla_credit
        self.tc, self.fc, self.sens, self.spec = est.tc, est.fc, est.sens, est.spec
        self.benign = float(est.params["callback"].get("benign_rate", 0.03))
        self.delay_shape, self.delay_scale = est.delay_shape, est.delay_scale_days
        self.delay_q = _gamma_quantiles(self.delay_shape, self.delay_scale)
        self.min_p = pub.planning.p0_min_success
        self.esc = pub.escalation_contractor
        self.att_limit = pub.attempt_limit_failures
        self.loss_h = {s: est.loss_hazard(s) for s in pub.severities}
        self.loss_amt = {s: est.loss_mean_dollars(s) for s in pub.severities}
        self.info = {s: est.info_transition(s) for s in pub.severities}
        self._phat: dict[tuple[str, str, int], float] = {}
        self.target_days = pub.closure_target_days
        tier = req.sla_tier or req.reported_severity
        self.closure_deadline = (req.arrival_tick + self.target_days[tier] * DAY - obs.tick) if req.first_closure_tick is None else None
        self.sla_deadline = None
        if req.first_start_tick is None and not req.sla_breached and req.sla_deadline_tick is not None:
            self.sla_deadline = float(req.sla_deadline_tick - obs.tick)
        self.sla_tier = req.sla_tier
        self.lead = {c: est.lead_days(c, self.k) * DAY for c in self.eligible}
        self.esc_delay = {c.contractor_id: pub.escalation_delay_minutes / c.speed for c in obs.contractors}

    # ---------------------------------------------------------------- helpers
    def phat(self, c: str, sev: str, j: int) -> float:
        key = (c, sev, j)
        v = self._phat.get(key)
        if v is None:
            v = self.est.p_success(c, self.k, sev, j, self.q)
            self._phat[key] = v
        return v

    def retention_increment(self, feat: str, w: float, t: float, H: float) -> float:
        if H <= 0:
            return 0.0
        t_rem = (H - t) / DAY
        if t_rem <= 0:
            return 0.0
        W = float(self.windows[feat])
        return self.h_now * (math.exp(self.beta[feat] * w) - 1.0) * min(W, t_rem) * self.fee_day * t_rem / 2.0

    def p0_contractor(self, sev: str, j: int, t: float, sla_pending: bool, deadline: Optional[float],
                      exclude: Optional[str]) -> str:
        pool = [c for c in self.eligible if c != exclude] if exclude is not None else list(self.eligible)
        if not pool:
            pool = list(self.eligible)
        best = None
        for c in pool:
            p = self.phat(c, sev, j)
            if p < self.min_p:
                continue
            if sla_pending and deadline is not None and t + self.lead[c] > deadline:
                continue
            key = (self.cmap[c].price_multiplier, c)
            if best is None or key < best[0]:
                best = (key, c)
        if best is not None:
            return best[1]
        return min(pool, key=lambda c: (-self.phat(c, sev, j), c))

    # ---------------------------------------------------------------- rollout
    def rollout(self, action: Action, U: np.ndarray, objective: str, H: float, myopic: bool) -> Outcome:
        """One sample. ``H`` is the horizon in minutes (0 for myopic)."""
        ui = 0
        n_u = U.shape[0]

        def nu() -> float:
            nonlocal ui
            v = U[ui % n_u]
            ui += 1
            return float(v)

        req = self.req
        cap = H if not myopic else self.pub.planning.myopic_safety_cap_days * DAY
        unresolved = nu() < self.b0
        sev = req.reported_severity
        j = req.attempt_index
        failures = req.observed_failure_count
        first_closed = req.first_closure_tick is not None
        sla_pending = self.sla_deadline is not None
        deadline = self.sla_deadline
        tier = self.sla_tier
        tier_unset = req.sla_tier is None and req.first_start_tick is None
        breached = req.sla_breached
        had_loss = req.had_severe_loss
        closed_unv = False
        is_closed = False
        t = 0.0
        op = 0.0
        pcost = 0.0
        ret = 0.0
        bonus = 0.0
        loss = False
        breach_new = False
        last_c = req.attempts[-1].contractor if req.attempts else None
        stage = req.stage
        last_report = req.attempts[-1].report if req.attempts else None
        first_action = True
        steps = 0
        max_steps = self.pub.planning.rollout_max_steps
        sw = self.windows

        def hazard_segment(t0: float, t1: float) -> None:
            nonlocal had_loss, loss, op, ret
            u = nu()
            if not unresolved or had_loss or t1 <= t0:
                return
            h = self.loss_h.get(sev, 0.0)
            if h <= 0:
                return
            days = (t1 - t0) / DAY
            p = 1.0 - (1.0 - h) ** days
            if u < p:
                tl = t0 + (t1 - t0) * (u / p)
                had_loss = True
                loss = True
                negligent = (is_closed and closed_unv) or breached
                if negligent:
                    op -= self.share * self.loss_amt.get(sev, 0.0)
                ret += self.retention_increment("sl", 1.0, tl, H)

        def charge(amount: float, proxy: bool = True) -> None:
            nonlocal op, pcost
            op -= amount
            if proxy:
                pcost += amount

        while True:
            steps += 1
            if steps > max_steps or t >= cap:
                break
            # --- choose the action at this decision point
            if first_action:
                atype, ac = action.type, action.contractor
                first_action = False
            else:
                if myopic:
                    break  # reached the next decision point
                atype, ac = self._rollout_rule(stage, sev, j, failures, last_report, last_c, t, sla_pending, deadline)
            # --- apply
            if atype == ActionType.TRIAGE:
                stage = Stage.DISPATCH_READY
                if tier_unset:
                    tier, tier_unset = sev, False
                    deadline = req.arrival_tick + self.pub.sla_target_hours[sev] * 60.0 - self.obs.tick
                    sla_pending = True
                continue
            if atype == ActionType.REQUEST_INFO:
                charge(self.costs["info"])
                t1 = t + self.pub.info_delay_days * DAY
                hazard_segment(t, min(t1, cap))
                if t1 >= cap:
                    t = t1
                    break
                t = t1
                row = self.info[sev]
                u = nu()
                acc = 0.0
                for s2 in self.pub.severities:
                    acc += row[s2]
                    if u < acc:
                        sev = s2
                        break
                stage = Stage.DISPATCH_READY
                if tier_unset:  # SLA tier is set at the first dispatch decision (SPEC 5.9)
                    tier, tier_unset = sev, False
                    deadline = req.arrival_tick + self.pub.sla_target_hours[sev] * 60.0 - self.obs.tick
                    sla_pending = True
                continue
            if atype == ActionType.DEFER:
                t1 = t + DAY
                hazard_segment(t, min(t1, cap))
                t = t1
                stage = Stage.DISPATCH_READY
                continue
            if atype in (ActionType.DISPATCH, ActionType.REDISPATCH, ActionType.ESCALATE):
                c = ac or self.esc
                charge(self.costs["dispatch"])
                if atype == ActionType.ESCALATE:
                    charge(self.costs["escalation"])
                    start = t + self.esc_delay[c]
                elif t == 0.0 and self.cmap[c].earliest_start_tick is not None:
                    start = float(self.cmap[c].earliest_start_tick - self.obs.tick)
                else:
                    start = t + self.lead.get(c, 2 * DAY)
                if sla_pending and deadline is not None:
                    if start > deadline and not breached:
                        tb = max(t, deadline)
                        if tb < cap:
                            breached = True
                            breach_new = True
                            charge(self.credit.get(tier or sev, 0.0))
                            ret += self.retention_increment("br", 1.0, tb, H)
                    sla_pending = False
                done = start + JOB_MINUTES
                hazard_segment(t, min(done, cap))
                if done >= cap:
                    t = done
                    break
                t = done
                p = self.phat(c, sev, j)
                success = (not unresolved) or (nu() < p)
                if success:
                    unresolved = False
                ur = nu()
                if success:
                    report = "complete" if ur < self.tc else "needs_return"
                else:
                    report = "complete" if ur < self.fc else "needs_return"
                inv = self.pub.invoice_base[self.k] * self.pub.invoice_severity_multiplier[sev] * self.cmap[c].price_multiplier
                ret += self.retention_increment("oc", inv / self.units / 100.0, t, H)
                j += 1
                last_c = c
                last_report = report
                if report == "needs_return":
                    failures += 1
                stage = Stage.WORK_REPORTED
                continue
            if atype == ActionType.VERIFY:
                charge(self.verify_cost)
                t1 = t + self.pub.verify_delay_days * DAY
                hazard_segment(t, min(t1, cap))
                if t1 >= cap:
                    t = t1
                    break
                t = t1
                uv = nu()
                if unresolved:
                    ok = uv >= self.sens
                else:
                    ok = uv < self.spec
                if ok:
                    stage = Stage.VERIFIED_OK
                else:
                    failures += 1
                    stage = Stage.VERIFIED_FAIL
                continue
            if atype == ActionType.CLOSE:
                closed_unv = stage == Stage.WORK_REPORTED
                is_closed = True
                if not first_closed:
                    first_closed = True
                    if self.closure_deadline is not None and t <= self.closure_deadline and (myopic or t <= H):
                        bonus = 1.0
                uc = nu()
                ud = nu()
                cb_time = None
                if unresolved:
                    pr = self.est.p_report(sev, closed_unv)
                    if uc < pr:
                        cb_time = t + self.delay_q[min(int(ud * N_QUANT), N_QUANT - 1)] * DAY
                elif uc < self.benign:
                    cb_time = t + ud * 30.0 * DAY
                if cb_time is None or cb_time >= cap:
                    hazard_segment(t, cap)
                    t = cap
                    break
                hazard_segment(t, cb_time)
                t = cb_time
                charge(self.costs["callback"])
                ret += self.retention_increment("cb", 1.0 / self.units, t, H)
                failures += 1
                is_closed = False
                stage = Stage.DISPATCH_READY
                continue
            raise ValueError(f"rollout cannot apply {atype}")  # pragma: no cover

        if objective == "proxy":
            score = bonus - self.pub.opex_weight * pcost / self.pub.opex_scale
        else:
            score = op - ret
        return Outcome(score, loss, breach_new, op, pcost, ret, bonus)

    def _rollout_rule(self, stage: Stage, sev: str, j: int, failures: int, last_report: Optional[str],
                      last_c: Optional[str], t: float, sla_pending: bool, deadline: Optional[float]) -> tuple[ActionType, Optional[str]]:
        """P0's rule with M's estimates (SPEC 9.1, 9.2)."""
        if stage == Stage.VERIFIED_OK:
            return ActionType.CLOSE, None
        if stage == Stage.WORK_REPORTED and last_report == "complete":
            return (ActionType.VERIFY, None) if sev == "moderate" else (ActionType.CLOSE, None)
        kind = ActionType.DISPATCH if stage == Stage.DISPATCH_READY else ActionType.REDISPATCH
        if failures >= self.att_limit or sev == "urgent":
            return ActionType.ESCALATE, self.esc
        exclude = last_c if stage in (Stage.WORK_REPORTED, Stage.VERIFIED_FAIL) else None
        return kind, self.p0_contractor(sev, j, t, sla_pending, deadline, exclude)


N_QUANT = 2048
_GQ_CACHE: dict[tuple[float, float], list[float]] = {}


def _gamma_quantiles(shape: float, scale: float) -> list[float]:
    key = (shape, scale)
    if key not in _GQ_CACHE:
        qs = (np.arange(N_QUANT) + 0.5) / N_QUANT
        _GQ_CACHE[key] = [float(x) for x in stats.gamma.ppf(qs, shape, scale=scale)]
    return _GQ_CACHE[key]


def uniform_matrix(seed: int, K: int) -> np.ndarray:
    g = np.random.Generator(np.random.PCG64DXSM(seed))
    return g.random((K, R_UNIFORMS))
