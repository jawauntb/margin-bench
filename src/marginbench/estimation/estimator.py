"""The shared frozen estimator M (SPEC 10). Every feasible policy uses the same instance.

This module is policy-side: it never imports ``environment/``. It holds only fitted
numbers loaded from ``models/estimator_v1.json``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marginbench.hashing import canonical_json, file_sha256

CONTRACTORS = ("A", "B", "C", "D")
CATS = ("plumbing", "electrical", "hvac", "general")
SEVS = ("minor", "moderate", "urgent")


def _expit(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def success_features(c: str, k: str, sev: str, j: int, q: float) -> list[float]:
    """Feature vector for the success model: one-hot contractor, category, reported
    severity, attempt index, condition grade."""
    return ([1.0 if c == x else 0.0 for x in CONTRACTORS] + [1.0 if k == x else 0.0 for x in CATS]
            + [1.0 if sev == x else 0.0 for x in SEVS] + [float(j), float(q)])


@dataclass(frozen=True)
class FrozenEstimator:
    params: dict[str, Any]

    # --- success -------------------------------------------------------------------------
    def p_success(self, c: str, k: str, sev: str, j: int, q: float) -> float:
        s = self.params["success"]
        x = success_features(c, k, sev, j, q)
        z = s["intercept"] + sum(w * v for w, v in zip(s["coef"], x))
        return _expit(z)

    @property
    def tc(self) -> float:  # P(report complete | success)
        return float(self.params["report_verify"]["tc"])

    @property
    def fc(self) -> float:  # P(report complete | failure): false-completion rate
        return float(self.params["report_verify"]["fc"])

    @property
    def sens(self) -> float:
        return float(self.params["report_verify"]["sens"])

    @property
    def spec(self) -> float:
        return float(self.params["report_verify"]["spec"])

    # --- callbacks -----------------------------------------------------------------------
    def p_report(self, sev: str, closed_unverified: bool) -> float:
        return float(self.params["callback"]["p_report"][sev]["1" if closed_unverified else "0"])

    @property
    def delay_shape(self) -> float:
        return float(self.params["report_delay"]["shape"])

    @property
    def delay_scale_days(self) -> float:
        return float(self.params["report_delay"]["scale_days"])

    # --- lead time -------------------------------------------------------------------------
    def lead_days(self, c: str, k: str) -> float:
        return float(self.params["lead_days"][c][k])

    # --- severe loss -------------------------------------------------------------------------
    def loss_hazard(self, sev: str) -> float:
        return float(self.params["severe_loss"]["daily_hazard"][sev])

    def loss_mean_dollars(self, sev: str) -> float:
        return float(self.params["severe_loss"]["mean_amount_dollars"][sev])

    # --- retention -----------------------------------------------------------------------
    def term_beta(self, feature: str) -> float:
        return float(self.params["termination"]["coef"][feature])

    def term_hazard(self, feats: dict[str, float]) -> float:
        t = self.params["termination"]
        lin = t["intercept"] + sum(t["coef"][f] * feats[f] for f in ("cb", "br", "sl", "oc"))
        return math.exp(min(lin, 50.0))

    # --- info resample -----------------------------------------------------------------------
    def info_transition(self, sev: str) -> dict[str, float]:
        return {k: float(v) for k, v in self.params["info"]["transition"][sev].items()}

    # --- beliefs -----------------------------------------------------------------------------
    def posterior_unresolved(self, prior_unres: float, p: float, report: str | None, verify: str | None) -> float:
        """P(unresolved) after an attempt with success prob p (if unresolved before), given
        the contractor report and optional verification result."""
        pu = prior_unres * (1.0 - p)  # unresolved after the attempt
        pr = 1.0 - pu
        if report == "complete":
            pu *= self.fc
            pr *= self.tc
        elif report == "needs_return":
            pu *= 1.0 - self.fc
            pr *= 1.0 - self.tc
        if verify == "ok":
            pu *= 1.0 - self.sens
            pr *= self.spec
        elif verify == "fail":
            pu *= self.sens
            pr *= 1.0 - self.spec
        tot = pu + pr
        return 0.5 if tot <= 0 else pu / tot

    # --- io ------------------------------------------------------------------------------------
    def to_json(self) -> str:
        return canonical_json(self.params)

    def save(self, path: str | Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json.loads(self.to_json()), sort_keys=True, indent=1) + "\n")
        return file_sha256(path)

    @classmethod
    def load(cls, path: str | Path) -> "FrozenEstimator":
        return cls(json.loads(Path(path).read_text()))
