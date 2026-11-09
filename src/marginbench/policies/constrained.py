"""P5 constrained economic-planning (SPEC 9.2): P4 restricted to actions whose estimates
satisfy relative risk constraints, with an always-legal fallback."""

from __future__ import annotations

from typing import Any

from marginbench.policies.mc import MCPolicy, _neg_key
from marginbench.schemas import ActionType, Observation, Stage


class P5ConstrainedPlanning(MCPolicy):
    name = "P5"
    objective = "econ"
    planning = True
    constrained = True

    def select(self, obs: Observation, vals: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
        pl = self.pub.planning
        r_min = min(v["p_loss"] for v in vals)
        b_min = min(v["p_breach"] for v in vals)
        loss_cap = max(pl.p5_loss_floor, r_min + pl.p5_loss_slack)
        sla_cap = max(pl.p5_sla_floor, b_min + pl.p5_sla_slack)
        ok = []
        for v in vals:
            if v["p_loss"] > loss_cap or v["p_breach"] > sla_cap:
                continue
            if v["action"].type == ActionType.CLOSE and v["b0"] > pl.p5_close_max_unresolved:
                continue
            ok.append(v)
        if len(ok) < len(vals):
            self.n_constraint_filtered += 1
        if ok:
            best = max(ok, key=lambda v: (v["q"], _neg_key(v["action"])))
            return best, "argmax_q_constrained"
        self.n_fallbacks += 1
        return self._fallback(obs, vals), "fallback"

    def _fallback(self, obs: Observation, vals: list[dict[str, Any]]) -> dict[str, Any]:
        by = {(v["action"].type, v["action"].contractor): v for v in vals}
        st = obs.request.stage
        if st == Stage.WORK_REPORTED and (ActionType.VERIFY, None) in by:
            return by[(ActionType.VERIFY, None)]
        if st == Stage.VERIFIED_OK and (ActionType.CLOSE, None) in by:
            return by[(ActionType.CLOSE, None)]
        q = obs.property.condition_grade
        req = obs.request

        def ph(c: str) -> float:
            return self.estimator.p_success(c, req.category, req.reported_severity, req.attempt_index, q)

        for kind in (ActionType.REDISPATCH, ActionType.DISPATCH, ActionType.ESCALATE):
            cands = [v for v in vals if v["action"].type == kind and v["action"].contractor]
            if cands:
                return min(cands, key=lambda v: (-ph(v["action"].contractor), v["action"].contractor))
        return min(vals, key=lambda v: v["action"].sort_key())
