"""Repair outcome and contractor report (SPEC 5.5, 5.6)."""

from __future__ import annotations

import math

from marginbench.config import Config
from marginbench.environment.contractors import expit


def success_probability(cfg: Config, logit_success: float, category_offset: float, true_severity: str,
                        condition: float, attempt_j: int) -> float:
    r = cfg.repair
    x = (logit_success + category_offset + r.b_sev[true_severity]
         + r.condition_coef * (condition - r.condition_center) + r.attempt_coef * attempt_j)
    return expit(x)


def repair_outcome(already_resolved: bool, p: float, u: float) -> bool:
    """Physical success. An attempt on an already-resolved request is a success."""
    if already_resolved:
        return True
    return u < p


def contractor_report(cfg: Config, success: bool, u: float) -> str:
    p_complete = cfg.report.complete_given_success if success else cfg.report.complete_given_failure
    return "complete" if u < p_complete else "needs_return"


def job_duration_minutes(cfg: Config, z: float) -> int:
    c = cfg.contractors
    return max(1, int(round(c.job_duration_median_minutes * math.exp(c.job_duration_log_sd * z))))
