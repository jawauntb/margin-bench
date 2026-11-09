"""Shared Monte Carlo action valuation (SPEC 9.1) used by P1-P5.

Matched compute: the same K, the same per-decision uniform matrix (derived from the
runner-supplied seed, so matched policies share samples), and the same rollout rule.
Ties break by action sort key.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np

from marginbench.policies.base import BasePolicy
from marginbench.policies.internal_model import RolloutContext, uniform_matrix
from marginbench.schemas import Action, ActionType, Observation

DAY = 1440.0


class MCPolicy(BasePolicy):
    objective = "econ"
    planning = True
    constrained = False

    def __init__(self, name: Optional[str] = None, K: Optional[int] = None, H_plan_days: Optional[int] = None) -> None:
        super().__init__()
        if name:
            self.name = name
        self._K = K
        self._H = H_plan_days
        self.n_samples = 0
        self.n_valued_decisions = 0
        self.wall = 0.0
        self.n_fallbacks = 0
        self.n_constraint_filtered = 0

    @property
    def K(self) -> int:
        assert self.pub is not None
        return self._K if self._K is not None else self.pub.planning.K

    @property
    def H_days(self) -> int:
        assert self.pub is not None
        if not self.planning:
            return 0
        return self._H if self._H is not None else self.pub.planning.H_plan_days

    def evaluate(self, obs: Observation, legal: tuple[Action, ...]) -> list[dict[str, Any]]:
        ctx = RolloutContext(obs, self.estimator, self.pub)
        U = uniform_matrix(obs.mc_seed, self.K)
        H = self.H_days * DAY
        myopic = not self.planning
        out = []
        for a in legal:
            scores, losses, breaches = [], 0, 0
            for k in range(self.K):
                o = ctx.rollout(a, U[k], self.objective, H, myopic)
                scores.append(o.score)
                losses += o.loss
                breaches += o.breach
            self.n_samples += self.K
            out.append({"action": a, "q": float(np.mean(scores)), "p_loss": losses / self.K,
                        "p_breach": breaches / self.K, "b0": ctx.b0})
        return out

    def select(self, obs: Observation, vals: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
        best = max(vals, key=lambda v: (v["q"], _neg_key(v["action"])))
        return best, "argmax_q"

    def act(self, observation: Observation, legal_actions: tuple[Action, ...]) -> Action:
        self.n_decisions += 1
        t0 = time.perf_counter()
        if len(legal_actions) == 1:
            a = legal_actions[0]
            self.wall += time.perf_counter() - t0
            return Action(a.request_id, a.stage, a.type, a.contractor, a.tick, reason_code="only_legal")
        self.n_valued_decisions += 1
        vals = self.evaluate(observation, legal_actions)
        best, why = self.select(observation, vals)
        a = best["action"]
        self.wall += time.perf_counter() - t0
        return Action(a.request_id, a.stage, a.type, a.contractor, a.tick, reason_code=why,
                      estimated_value=best["q"], estimated_risk=best["p_loss"])

    def diagnostics(self) -> dict[str, object]:
        d = super().diagnostics()
        d.update({"K": self.K, "H_plan_days": self.H_days, "objective": self.objective, "samples": self.n_samples,
                  "valued_decisions": self.n_valued_decisions, "wall_seconds": round(self.wall, 3),
                  "fallbacks": self.n_fallbacks, "constraint_filtered_decisions": self.n_constraint_filtered})
        return d


def _neg_key(a: Action) -> tuple:
    """Max over this key prefers the smallest action sort key on ties."""
    o, c = a.sort_key()
    return (-o, tuple(-ord(ch) for ch in c))
