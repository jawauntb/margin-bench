"""Estimator audit (SPEC 10.3): Brier scores, calibration curves, sample sizes, censoring
fractions, per-category error, and an evaluator-side coefficient-vs-truth comparison."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from marginbench.config import CATEGORIES, Config
from marginbench.estimation.estimator import CATS, CONTRACTORS, FrozenEstimator


def calibration_curve(p: np.ndarray, y: np.ndarray, bins: int = 10) -> list[dict[str, Any]]:
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        if m.sum() == 0:
            continue
        out.append({"bin_low": float(edges[i]), "bin_high": float(edges[i + 1]), "n": int(m.sum()),
                    "mean_pred": float(p[m].mean()), "mean_obs": float(y[m].mean())})
    return out


def ece(curve: list[dict[str, Any]]) -> float:
    n = sum(c["n"] for c in curve)
    return float(sum(c["n"] * abs(c["mean_pred"] - c["mean_obs"]) for c in curve) / max(n, 1))


def audit_estimator(est: FrozenEstimator, fit_info: dict[str, Any], cfg: Config) -> dict[str, Any]:
    rep = fit_info["report"]
    Xs, ys = fit_info["calib_success"]
    ps = np.asarray([est.p_success(*_decode(x)) for x in Xs]) if len(Xs) else np.zeros(0)
    curve_s = calibration_curve(ps, ys) if len(ys) else []
    per_cat = {}
    for j, k in enumerate(CATS):
        m = Xs[:, 4 + j] == 1.0 if len(Xs) else np.zeros(0, dtype=bool)
        if m.sum():
            per_cat[k] = {"n": int(m.sum()), "mean_pred": float(ps[m].mean()), "mean_obs": float(ys[m].mean()),
                          "brier": float(np.mean((ps[m] - ys[m]) ** 2))}
    Xc, yc = fit_info["calib_callback"]
    pc = Xc[:, 0] if len(Xc) else np.zeros(0)
    curve_c = calibration_curve(pc, yc) if len(yc) else []

    c_tr = rep["success"]["train_counts"]
    censor = {
        "success_immature_fraction": c_tr["immature"] / max(c_tr["attempts"], 1),
        "success_unlabeled_excluded_fraction": c_tr["unlabeled_excluded"] / max(c_tr["attempts"], 1),
        "callback_immature_fraction": rep["callback"]["n_train_immature_excluded"]
        / max(rep["callback"]["n_train_matured"] + rep["callback"]["n_train_immature_excluded"], 1),
        "report_delay_censored_at_days": rep["report_delay"]["censored_at_days"],
    }
    # evaluator-side truth comparison (diagnostic only; never available to policies)
    fx = {f.id: f for f in cfg.contractors.fixtures}
    truth_success = {}
    for c in CONTRACTORS:
        lg = math.log(fx[c].success / (1 - fx[c].success))
        q = 5.0 / 7.0
        true_p = 1 / (1 + math.exp(-(lg + cfg.repair.condition_coef * (q - cfg.repair.condition_center))))
        k = "general" if "general" in fx[c].eligible else fx[c].eligible[0]
        truth_success[c] = {"true_moderate_j0_qmean": true_p, "estimated": est.p_success(c, k, "moderate", 0, q)}
    betas = cfg.retention.betas()
    truth = {
        "success_by_contractor": truth_success,
        "report_verify": {"tc": [cfg.report.complete_given_success, est.tc], "fc": [cfg.report.complete_given_failure, est.fc],
                          "sens": [cfg.verify.sensitivity, est.sens], "spec": [cfg.verify.specificity, est.spec]},
        "p_report_unverified": {s: [0.8 * cfg.m_sev(s) * cfg.m_close_unverified(), est.p_report(s, True)]
                                for s in ("minor", "moderate", "urgent")},
        "p_report_verified": {s: [0.8 * cfg.m_sev(s), est.p_report(s, False)] for s in ("minor", "moderate", "urgent")},
        "loss_hazard_by_true_sev_vs_est_by_reported": {s: [cfg.loss_hazard(s), est.loss_hazard(s)]
                                                      for s in ("minor", "moderate", "urgent")},
        "termination": {"log_h0": [math.log(cfg.retention.h0), est.params["termination"]["intercept"]],
                        **{f: [betas[f], est.term_beta(f), est.params["termination"]["se"][f]] for f in ("cb", "br", "sl", "oc")}},
        "report_delay": {"shape": [cfg.callbacks.delay_gamma_shape, est.delay_shape],
                         "scale_days": [cfg.callbacks.delay_gamma_scale_days, est.delay_scale_days]},
        "note": "pairs are [truth, estimate]; truth uses fixture means, mean tenant propensity 0.8 and mean q 5/7",
    }
    return {
        "label": "estimator audit (evaluator-side; truth comparisons are diagnostics only)",
        "success_model": {"brier_calib": float(np.mean((ps - ys) ** 2)) if len(ys) else None,
                          "ece_calib": ece(curve_s) if curve_s else None, "calibration_curve": curve_s,
                          "n_calib": int(len(ys)), "per_category": per_cat, **rep["success"]},
        "callback_model": {"brier_calib": float(np.mean((pc - yc) ** 2)) if len(yc) else None,
                           "ece_calib": ece(curve_c) if curve_c else None, "calibration_curve": curve_c,
                           "n_calib": int(len(yc)), **rep["callback"]},
        "censoring": censor,
        "report_delay": rep["report_delay"],
        "severe_loss": rep["severe_loss"],
        "termination": rep["termination"],
        "info": rep["info"],
        "lead_days_n": rep["lead_days_n"],
        "truth_comparison": truth,
    }


def _decode(x: np.ndarray) -> tuple[str, str, str, int, float]:
    c = CONTRACTORS[int(np.argmax(x[0:4]))]
    k = CATS[int(np.argmax(x[4:8]))]
    s = ("minor", "moderate", "urgent")[int(np.argmax(x[8:11]))]
    return c, k, s, int(x[11]), float(x[12])
