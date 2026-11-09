"""P0, the operating baseline (SPEC 9.2): deterministic rules.

Source of p-hat: before the estimator M exists (history generation) P0 uses the public
prior p-hat = 0.80 for every contractor, so the rule reduces to "cheapest eligible
contractor that meets SLA". After M is frozen, P0 uses M's p-hat (DECISIONS D-14).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from marginbench.policies.base import BasePolicy
from marginbench.schemas import Action, ActionType, ContractorView, Observation, RequestView, Stage

PHat = Callable[[str, str, str, int, float], float]


def p0_choose_contractor(
    req: RequestView,
    contractors: tuple[ContractorView, ...],
    candidates: list[str],
    phat: PHat,
    q_obs: float,
    min_success: float,
    exclude: Optional[str],
) -> str:
    """Lowest-price eligible contractor with p-hat >= min_success whose expected start meets
    SLA; ties to the lower id; else the highest-p-hat eligible contractor."""
    cmap = {c.contractor_id: c for c in contractors}
    pool = [c for c in candidates if c != exclude] if exclude is not None else list(candidates)
    if not pool:
        pool = list(candidates)
    sla_pending = req.first_start_tick is None and not req.sla_breached and req.sla_deadline_tick is not None
    ps = {c: phat(c, req.category, req.reported_severity, req.attempt_index, q_obs) for c in pool}
    qual = []
    for c in pool:
        if ps[c] < min_success:
            continue
        st = cmap[c].earliest_start_tick
        if sla_pending and (st is None or st > (req.sla_deadline_tick or 0)):
            continue
        qual.append(c)
    if qual:
        return min(qual, key=lambda c: (cmap[c].price_multiplier, c))
    return min(pool, key=lambda c: (-ps[c], c))


def p0_action(obs: Observation, legal: tuple[Action, ...], phat: PHat, min_success: float, esc_contractor: str) -> Action:
    req = obs.request
    st = req.stage
    by_type: dict[ActionType, list[Action]] = {}
    for a in legal:
        by_type.setdefault(a.type, []).append(a)
    if st == Stage.NEW:
        return by_type[ActionType.TRIAGE][0]
    if st == Stage.VERIFIED_OK:
        return by_type[ActionType.CLOSE][0]
    if st == Stage.WORK_REPORTED and req.attempts and req.attempts[-1].report == "complete":
        want = ActionType.VERIFY if req.reported_severity == "moderate" else ActionType.CLOSE
        return by_type[want][0]
    # dispatch-like decision: DISPATCH_READY, WORK_REPORTED(needs_return), VERIFIED_FAIL
    disp_type = ActionType.DISPATCH if st == Stage.DISPATCH_READY else ActionType.REDISPATCH
    disp = by_type.get(disp_type, [])
    esc = by_type.get(ActionType.ESCALATE, [])
    if not disp:  # reported urgent or attempt limit: escalate(C) when legal, else the only escalation
        for a in esc:
            if a.contractor == esc_contractor:
                return a
        return esc[0]
    exclude = None
    if st in (Stage.WORK_REPORTED, Stage.VERIFIED_FAIL) and req.attempts:
        exclude = req.attempts[-1].contractor
    cands = [a.contractor for a in disp if a.contractor is not None]
    chosen = p0_choose_contractor(req, obs.contractors, cands, phat, obs.property.condition_grade, min_success, exclude)
    for a in disp:
        if a.contractor == chosen:
            return a
    raise AssertionError("P0 chose a contractor outside the legal set")  # pragma: no cover


class P0Baseline(BasePolicy):
    name = "P0"

    def __init__(self, use_prior: bool = False) -> None:
        super().__init__()
        self.use_prior = use_prior

    def _phat(self) -> PHat:
        assert self.pub is not None
        if self.use_prior or self.estimator is None:
            prior = self.pub.planning.p0_prior_success
            return lambda c, k, s, j, q: prior
        return self.estimator.p_success

    def act(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        assert self.pub is not None
        self.n_decisions += 1
        a = p0_action(observation, legal_actions, self._phat(), self.pub.planning.p0_min_success,
                      self.pub.escalation_contractor)
        return Action(a.request_id, a.stage, a.type, a.contractor, a.tick, reason_code="p0_rule")


class BehaviorPolicy(BasePolicy):
    """History logging policy (SPEC 10.1): P0's action w.p. p0_prob, else uniform over legal
    actions. Randomness comes from the runner-supplied per-decision seed. Propensities logged."""

    name = "BEHAVIOR"

    def __init__(self, p0_prob: float) -> None:
        super().__init__()
        self.p0_prob = p0_prob
        self.last_propensity: Optional[float] = None
        self._p0 = P0Baseline(use_prior=True)

    def reset(self, public_config: Any, estimator: Any, initial_observation: Any) -> None:
        super().reset(public_config, estimator, initial_observation)
        self._p0.reset(public_config, None, initial_observation)

    def act(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        import numpy as np

        self.n_decisions += 1
        g = np.random.Generator(np.random.PCG64DXSM(observation.mc_seed))
        u, v = g.random(2)
        p0a = self._p0.act(observation, legal_actions)
        n = len(legal_actions)
        if u < self.p0_prob:
            chosen = p0a
        else:
            chosen = legal_actions[min(int(v * n), n - 1)]
        same = (chosen.type, chosen.contractor) == (p0a.type, p0a.contractor)
        self.last_propensity = self.p0_prob * float(same) + (1.0 - self.p0_prob) / n
        return Action(chosen.request_id, chosen.stage, chosen.type, chosen.contractor, chosen.tick, reason_code="behavior")
