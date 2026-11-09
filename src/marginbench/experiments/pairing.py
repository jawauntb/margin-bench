"""Paired contrasts across arms of the same replication (SPEC 2.3, 14)."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from marginbench.evaluation.classification import PROXY_REVERSAL, VALUE, evaluate_contrast
from marginbench.evaluation.statistics import bootstrap_ci, cvar, holm, paired_summary

PROXY_REVERSAL_PAIRS = {("P2", "P0"), ("P1", "P0")}


def contrast_type(a: str, b: str) -> str:
    return PROXY_REVERSAL if (a, b) in PROXY_REVERSAL_PAIRS else VALUE


def world_status(results: list[dict[str, Any]], world: str) -> str:
    st = "VALID"
    for r in results:
        if r["world"] != world:
            continue
        for arm in r["arms"].values():
            if arm["status"] == "INVALID":
                return "INVALID"
            if arm["status"] == "RESOURCE_LIMIT":
                st = "RESOURCE_LIMIT"
    return st


def paired_rows(results: list[dict[str, Any]], world: str, a: str, b: str, experiment: str) -> list[dict[str, Any]]:
    rows = []
    for r in results:
        if r["world"] != world or a not in r["arms"] or b not in r["arms"]:
            continue
        A, B = r["arms"][a], r["arms"][b]
        ga, gb = A["G"], B["G"]
        rows.append({
            "experiment": experiment, "world": world, "replication": r["replication"], "contrast": f"{a}-{b}",
            "a": a, "b": b, "J_a": A["J"], "J_b": B["J"], "dJ": A["J"] - B["J"],
            "G_a": ga, "G_b": gb, "dG": (ga - gb) if (ga is not None and gb is not None) else None,
            "status_a": A["status"], "status_b": B["status"],
            "event_hash_a": A["event_hash"], "event_hash_b": B["event_hash"],
        })
    return rows


def analyze_contrasts(results: list[dict[str, Any]], world: str, contrasts: list[tuple[str, str]], m: float,
                      experiment: str, primary: Optional[tuple[str, str]] = None,
                      confirmatory: Optional[list[tuple[str, str]]] = None, verified: bool = True,
                      run_status_override: Optional[str] = None) -> dict[str, Any]:
    """Classifies every contrast in one world. If ``confirmatory`` is given, those contrasts
    form the Holm family; ``primary`` is unadjusted at alpha 0.05; everything else is
    EXPLORATORY at alpha 0.05."""
    status = run_status_override or world_status(results, world)
    rows_by = {(a, b): paired_rows(results, world, a, b, experiment) for a, b in contrasts}
    holm_res: dict[str, Any] = {}
    if confirmatory:
        pv = {}
        for a, b in confirmatory:
            dj = [x["dJ"] for x in rows_by[(a, b)] if x["status_a"] == "VALID" and x["status_b"] == "VALID"]
            s = paired_summary(dj)
            pv[f"{a}-{b}"] = s.p_value if s.p_value is not None else 1.0
        holm_res = holm(pv)
    out = {}
    for a, b in contrasts:
        rows = rows_by[(a, b)]
        ok = [x for x in rows if x["status_a"] == "VALID" and x["status_b"] == "VALID"]
        dj = [x["dJ"] for x in ok]
        dg = [x["dG"] for x in ok if x["dG"] is not None]
        key = f"{a}-{b}"
        label = "EXPLORATORY"
        alpha = 0.05
        stopped = False
        if primary is not None and (a, b) == primary:
            label = "PRIMARY"
        elif confirmatory and (a, b) in confirmatory:
            label = "CONFIRMATORY"
            alpha = holm_res[key]["alpha"]
            stopped = holm_res[key]["stopped"]
        res = evaluate_contrast(a, b, contrast_type(a, b), dj, dg, m, alpha=alpha, run_status=status,
                                verified=verified, holm_stopped=stopped, label=label).to_dict()
        res["n_pairs"] = len(rows)
        res["n_valid_pairs"] = len(ok)
        res["n_undefined_G"] = len(ok) - len(dg)
        if label == "CONFIRMATORY":
            res["holm"] = holm_res[key]
        out[key] = res
    return {"world": world, "status": status, "materiality": m, "contrasts": out,
            "holm": holm_res}


def arm_summary(results: list[dict[str, Any]], world: str, policy: str, j_p0_q05: Optional[float],
                seed: int) -> dict[str, Any]:
    arms = [r["arms"][policy] for r in results if r["world"] == world and policy in r["arms"]]
    J = [a["J"] for a in arms]
    G = [a["G"] for a in arms if a["G"] is not None]
    out: dict[str, Any] = {"n": len(arms), "J": paired_summary(J).to_dict(), "G": paired_summary(G).to_dict() if G else None}
    keys = ("closure_rate", "verified_resolution_rate", "true_resolution_rate", "callback_rate_per_completed_attempt",
            "reopen_rate", "opex_per_request", "time_to_first_closure_days_mean", "time_to_verified_resolution_days_mean",
            "backlog_at_cutoff", "backlog_age_days", "escalation_rate", "verification_rate", "unreported_failure_count",
            "severe_loss_count", "sla_breach_count", "callback_count", "contracts_lost", "nominal_contribution_dollars")
    means = {}
    for k in keys:
        vals = [a["metrics"][k] for a in arms if a["metrics"].get(k) is not None]
        means[k] = {"mean": float(np.mean(vals)) if vals else None, "n_defined": len(vals),
                    "null_reason": None if vals else "undefined in every replication"}
    out["metrics_mean"] = means
    cats: dict[str, list[float]] = {}
    for a in arms:
        for c, v in a["metrics"]["operator_by_category_dollars"].items():
            cats.setdefault(c, []).append(v)
        for c, v in a["metrics"]["owner_by_category_dollars"].items():
            cats.setdefault("owner:" + c, []).append(v)
    out["by_category_mean_dollars"] = {c: float(np.mean(v)) for c, v in sorted(cats.items())}
    losses = [a["metrics"]["losses_by_principal_dollars"]["OPERATOR"] for a in arms]
    n_tail = sum(1 for a in arms if a["metrics"]["severe_loss_count"] > 0)
    out["risk"] = {
        "p_J_below_p0_q05": (float(np.mean([j < j_p0_q05 for j in J])) if (J and j_p0_q05 is not None) else None),
        "J_quantiles": {q: float(np.quantile(J, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)} if J else None,
        "cvar5_J": cvar(J, 0.05) if len(J) >= 20 else None,
        "cvar5_note": None if len(J) >= 20 else "fewer than 20 replications",
        "replications_with_severe_loss": n_tail,
        "operator_loss_mean_dollars": float(np.mean(losses)) if losses else None,
        "operator_loss_bootstrap_ci": bootstrap_ci(losses, seed=seed) if losses else None,
        "bootstrap_reliable": n_tail >= 20,
        "severe_loss_frequency_realized": float(np.mean([a["metrics"]["severe_loss_count"] for a in arms])) if arms else None,
    }
    diags = [a["diagnostics"].get(policy, {}) for a in arms]
    if diags and any("samples" in d for d in diags):
        dec = sum(d.get("valued_decisions", 0) for d in diags)
        out["compute"] = {"samples": int(sum(d.get("samples", 0) for d in diags)),
                          "decisions": int(sum(d.get("decisions", 0) for d in diags)),
                          "valued_decisions": int(dec),
                          "wall_seconds": float(sum(d.get("wall_seconds", 0.0) for d in diags)),
                          "fallbacks": int(sum(d.get("fallbacks", 0) for d in diags)),
                          "constraint_filtered_decisions": int(sum(d.get("constraint_filtered_decisions", 0) for d in diags)),
                          "fallback_rate": (sum(d.get("fallbacks", 0) for d in diags) / dec) if dec else None,
                          "constraint_filter_rate": (sum(d.get("constraint_filtered_decisions", 0) for d in diags) / dec) if dec else None,
                          "K": diags[0].get("K"), "H_plan_days": diags[0].get("H_plan_days")}
    return out
