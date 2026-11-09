"""P6 oracle: NON-DEPLOYABLE DIAGNOSTIC (SPEC 9.2, Tier 3).

P4's economic planning objective with the true parameters and the latent state of the
replication. It deliberately breaks the information boundary: the runner hands it the
authoritative engine after construction. It is excluded from "best evaluated policy" and
from every confirmatory comparison, and every artifact labels it. It imports nothing from
``environment/``; it reads the engine object it is handed.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from marginbench.policies.internal_model import RolloutContext, uniform_matrix
from marginbench.policies.mc import MCPolicy

LABEL = "NON-DEPLOYABLE DIAGNOSTIC"


class _TruthEstimator:
    """Duck-typed estimator answering with the replication's true mechanism for one request."""

    def __init__(self, eng: Any, req: Any, base: Any) -> None:
        self.eng, self.req, self.base = eng, req, base
        self.cfg = eng.cfg
        self.params = {"callback": {"benign_rate": 0.0 if self.cfg.callbacks.off else self.cfg.callbacks.benign_prob}}
        self.prop = eng.properties[req.property_id]
        self.tenant = eng.tenants[req.tenant_id]
        sens, spec = self.cfg.verify_rates()
        self.tc, self.fc, self.sens, self.spec = (self.cfg.report.complete_given_success,
                                                  self.cfg.report.complete_given_failure, sens, spec)
        self.delay_shape = self.cfg.callbacks.delay_gamma_shape
        self.delay_scale_days = self.cfg.callbacks.delay_gamma_scale_days

    def p_success(self, c: str, k: str, sev: str, j: int, q: float) -> float:
        cs = self.eng.contractors[c]
        r = self.cfg.repair
        x = (cs.logit_success + cs.category_offsets[k] + r.b_sev[self.req.true_severity]
             + r.condition_coef * (self.prop.condition - r.condition_center) + r.attempt_coef * j)
        return 1.0 / (1.0 + math.exp(-x))

    def posterior_unresolved(self, prior: float, p: float, report: Any, verify: Any) -> float:
        return 0.0 if self.req.physical_resolved else 1.0

    def p_report(self, sev: str, cu: bool) -> float:
        if self.cfg.callbacks.off:
            return 0.0
        mc = self.cfg.m_close_unverified() if cu else 1.0
        return min(1.0, self.tenant.report_propensity * self.cfg.m_sev(self.req.true_severity) * mc)

    def lead_days(self, c: str, k: str) -> float:
        return self.base.lead_days(c, k)

    def loss_hazard(self, sev: str) -> float:
        return 0.0 if self.req.had_severe_loss else self.cfg.loss_hazard(self.req.true_severity)

    def loss_mean_dollars(self, sev: str) -> float:
        return self.cfg.loss.median_amount[self.req.true_severity] * math.exp(self.cfg.loss.log_sd ** 2 / 2)

    def term_beta(self, f: str) -> float:
        return self.cfg.retention.betas()[f]

    def term_hazard(self, feats: dict[str, float]) -> float:
        b = self.cfg.retention.betas()
        return self.cfg.retention.h0 * math.exp(sum(b[k] * feats[k] for k in b))

    def info_transition(self, sev: str) -> dict[str, float]:
        return self.base.info_transition(sev)


class P6Oracle(MCPolicy):
    name = "P6"
    objective = "econ"
    planning = True
    label = LABEL

    def __init__(self, K: Optional[int] = None, H_plan_days: Optional[int] = None) -> None:
        super().__init__(K=K, H_plan_days=H_plan_days)
        self._eng: Any = None

    def attach_privileged(self, world: Any) -> None:
        self._world = world

    def attach_engine_truth(self, eng: Any) -> None:
        self._eng = eng

    def evaluate(self, obs: Any, legal: Any) -> list[dict[str, Any]]:
        req = self._eng.requests[obs.request.request_id]
        truth = _TruthEstimator(self._eng, req, self.estimator)
        ctx = RolloutContext(obs, truth, self.pub)
        ctx.b0 = 0.0 if req.physical_resolved else 1.0
        U = uniform_matrix(obs.mc_seed, self.K)
        H = self.H_days * 1440.0
        out = []
        for a in legal:
            scores, losses, breaches = [], 0, 0
            for k in range(self.K):
                o = ctx.rollout(a, U[k], self.objective, H, False)
                scores.append(o.score)
                losses += o.loss
                breaches += o.breach
            self.n_samples += self.K
            out.append({"action": a, "q": sum(scores) / len(scores), "p_loss": losses / self.K,
                        "p_breach": breaches / self.K, "b0": ctx.b0})
        return out

    def diagnostics(self) -> dict[str, object]:
        d = super().diagnostics()
        d["label"] = LABEL
        return d
