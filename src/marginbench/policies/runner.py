"""Policy factory. Feasible policies (P0-P5) and their perturbed E9 variants."""

from __future__ import annotations

from typing import Any, Optional

from marginbench.policies.baseline import P0Baseline
from marginbench.policies.constrained import P5ConstrainedPlanning
from marginbench.policies.economic import P3EconomicMyopic, P4EconomicPlanning
from marginbench.policies.mc import MCPolicy
from marginbench.policies.proxy import P1ProxyMyopic, P2ProxyPlanning

FEASIBLE = ("P0", "P1", "P2", "P3", "P4", "P5")
CLASSES = {"P1": P1ProxyMyopic, "P2": P2ProxyPlanning, "P3": P3EconomicMyopic, "P4": P4EconomicPlanning,
           "P5": P5ConstrainedPlanning}


class VariantPolicy(MCPolicy):
    """E9 perturbed candidate: an objective, a planning horizon (0 = myopic) and two tweaks:
    a close threshold (close only if P(unresolved) <= tau) and a verification propensity
    (an additive bonus on verify's estimated value). Identical estimator, K and seeds."""

    def __init__(self, name: str, objective: str, H_plan_days: int, close_tau: Optional[float],
                 verify_bonus: float, K: Optional[int] = None) -> None:
        super().__init__(name=name, K=K, H_plan_days=H_plan_days)
        self.objective = objective
        self.planning = H_plan_days > 0
        self.close_tau = close_tau
        self.verify_bonus = verify_bonus

    def select(self, obs, vals):
        from marginbench.policies.mc import _neg_key
        from marginbench.schemas import ActionType

        adj = []
        for v in vals:
            q = v["q"]
            if v["action"].type == ActionType.VERIFY:
                q += self.verify_bonus
            if v["action"].type == ActionType.CLOSE and self.close_tau is not None and v["b0"] > self.close_tau:
                q = float("-inf") if len(vals) > 1 else q
            adj.append({**v, "q_adj": q})
        best = max(adj, key=lambda v: (v["q_adj"], _neg_key(v["action"])))
        return best, "argmax_q_variant"


def make_policy(name: str, K: Optional[int] = None, H_plan_days: Optional[int] = None,
                variant: Optional[dict[str, Any]] = None) -> Any:
    if variant is not None:
        return VariantPolicy(name=name, objective=variant["objective"], H_plan_days=int(variant["H_plan_days"]),
                             close_tau=variant.get("close_tau"), verify_bonus=float(variant.get("verify_bonus", 0.0)), K=K)
    if name == "P0":
        return P0Baseline()
    if name == "P6":
        from marginbench.policies.oracle import P6Oracle

        return P6Oracle(K=K, H_plan_days=H_plan_days)
    cls = CLASSES[name]
    return cls(K=K, H_plan_days=H_plan_days)
