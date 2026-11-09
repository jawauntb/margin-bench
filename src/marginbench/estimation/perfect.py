"""Perfect-estimator diagnostic (SPEC 13 ablations): M with population-true parameters
taken from the config. Labeled diagnostic; it is not a feasible estimator. It knows the
population mechanism but not per-replication perturbations or latent state."""

from __future__ import annotations

import math
from typing import Any

from marginbench.config import Config
from marginbench.estimation.estimator import CATS, CONTRACTORS, SEVS, FrozenEstimator


def perfect_estimator(cfg: Config, template: FrozenEstimator) -> FrozenEstimator:
    fx = {f.id: f for f in cfg.contractors.fixtures}
    r = cfg.repair
    coef = []
    for c in CONTRACTORS:
        s = cfg.contractors.identical_quality_value if cfg.contractors.identical_quality else fx[c].success
        coef.append(math.log(s / (1 - s)))
    coef += [0.0] * len(CATS)
    coef += [r.b_sev[s] for s in SEVS]
    coef += [r.attempt_coef, r.condition_coef]
    sens, spec = cfg.verify_rates()
    rho_mean = cfg.portfolio.tenant_report_beta_a / (cfg.portfolio.tenant_report_beta_a + cfg.portfolio.tenant_report_beta_b)
    p_report = {s: {"0": (0.0 if cfg.callbacks.off else min(1.0, rho_mean * cfg.m_sev(s))),
                    "1": (0.0 if cfg.callbacks.off else min(1.0, rho_mean * cfg.m_sev(s) * cfg.m_close_unverified()))}
                for s in SEVS}
    betas = cfg.retention.betas()
    params: dict[str, Any] = {
        "version": "estimator_perfect_diagnostic",
        "label": "PERFECT-ESTIMATOR DIAGNOSTIC (not feasible)",
        "success": {"intercept": -r.condition_coef * r.condition_center, "coef": coef},
        "report_verify": {"tc": cfg.report.complete_given_success, "fc": cfg.report.complete_given_failure,
                          "sens": sens, "spec": spec},
        "callback": {"p_report": p_report, "benign_rate": 0.0 if cfg.callbacks.off else cfg.callbacks.benign_prob},
        "report_delay": {"shape": cfg.callbacks.delay_gamma_shape, "scale_days": cfg.callbacks.delay_gamma_scale_days},
        "lead_days": template.params["lead_days"],
        "severe_loss": {"daily_hazard": {s: cfg.loss_hazard(s) for s in SEVS},
                        "mean_amount_dollars": {s: cfg.loss.median_amount[s] * math.exp(cfg.loss.log_sd ** 2 / 2) for s in SEVS}},
        "termination": {"intercept": math.log(cfg.retention.h0), "coef": dict(betas)},
        "info": template.params["info"],
    }
    return FrozenEstimator(params)
