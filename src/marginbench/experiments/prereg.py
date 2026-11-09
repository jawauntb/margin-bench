"""Preregistration (SPEC 12, 14.3, 14.5): calib materiality and power, plan.yaml,
EXPERIMENT_PLAN.md, and the evaluate guard."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from marginbench.config import REPO_ROOT, load_config
from marginbench.evaluation.provenance import code_state, git
from marginbench.evaluation.statistics import achieved_power, materiality, n_eval_from
from marginbench.hashing import file_sha256

PLAN_PATH = REPO_ROOT / "configs" / "plan.yaml"
EST_PATH = REPO_ROOT / "models" / "estimator_v1.json"


def calib_analysis(estimator_path: str, workers: int = 4, n: int = 20) -> dict[str, Any]:
    from marginbench.experiments.runner import make_jobs, run_jobs

    cfg = load_config()
    jobs = make_jobs("CALIB", "default", cfg, estimator_path, "calib", list(range(n)), [{"name": "P0"}, {"name": "P2"}],
                     trace_dir=None)
    t0 = time.perf_counter()
    res, status = run_jobs(jobs, None, workers=workers)
    wall = time.perf_counter() - t0
    j0 = [r["arms"]["P0"]["J"] for r in res]
    d = [r["arms"]["P2"]["J"] - r["arms"]["P0"]["J"] for r in res]
    m = materiality(float(np.mean(j0)))
    s = float(np.std(d, ddof=1))
    nn = n_eval_from(s, m)
    per_rep = {"P0": float(np.mean([r["arms"]["P0"]["wall_seconds"] for r in res])),
               "P2": float(np.mean([r["arms"]["P2"]["wall_seconds"] for r in res]))}
    return {"status": status, "n": n, "mean_J_P0": float(np.mean(j0)), "materiality_dollars": m,
            "sd_dJ_P2_P0": s, "mean_dJ_P2_P0": float(np.mean(d)), **nn,
            "achieved_power": {"effect_m": achieved_power(s, m, nn["n_eval"], m),
                               "effect_2m": achieved_power(s, m, nn["n_eval"], 2 * m)},
            "power_note": "At |dJ| = m exactly, power is about 50% by construction (the point estimate must pass m).",
            "calib_wall_seconds": wall, "per_replication_seconds": per_rep,
            "replication_hashes": {r["replication"]: {p: a["event_hash"] for p, a in r["arms"].items()} for r in res}}


def projected_primary_seconds(per_rep: dict[str, float], n_eval: int, workers: int) -> float:
    mc = per_rep["P2"]
    return n_eval * (per_rep["P0"] + 5 * mc) / max(workers, 1)


def build_plan(calib: dict[str, Any], workers: int) -> dict[str, Any]:
    from marginbench.experiments.ablations import ABLATIONS, CONFIRMATORY, PRIMARY_CONTRAST, catalog
    from marginbench.experiments.e9_gates import generate_variants
    from marginbench.experiments.sensitivity import DIMS, latin_hypercube

    cfg = load_config()
    n_eval = int(calib["n_eval"])
    proj = projected_primary_seconds(calib["per_replication_seconds"], n_eval, workers)
    K = cfg.planning.K
    k_note = f"projected PRIMARY {proj / 3600:.2f} h with {workers} workers at K={K}: no K reduction needed"
    if proj > 3 * 3600:
        K = max(16, int(K * 3 * 3600 / proj))
        k_note = f"projected PRIMARY {proj / 3600:.2f} h exceeded 3 h: K reduced to {K} for all planning policies"
    cat = catalog(n_eval)
    e9_seed = cfg.seeds.eval + 909
    sens_seed = cfg.seeds.sens
    plan = {
        "plan_version": "plan v1",
        "label": "OPEN_PREREGISTERED",
        "evaluation_is_blind": False,
        "versions": cfg.versions.model_dump(),
        "estimator": {"path": "models/estimator_v1.json", "sha256": file_sha256(EST_PATH)},
        "base_config": {"path": "configs/default.yaml", "config_hash": cfg.config_hash()},
        "primary": {"contrast": list(PRIMARY_CONTRAST), "type": "proxy_reversal", "alpha": 0.05, "ci": "two-sided Student-t 95%",
                    "scenario": "default", "partition": "eval", "n": n_eval},
        "confirmatory_family": {"contrasts": [list(c) for c in CONFIRMATORY], "types": {"P1-P0": "proxy_reversal"},
                                "method": "Holm on paired t-test p-values, family alpha 0.05, stop at first non-rejection",
                                "scenario": "default"},
        "exploratory": "every other contrast and experiment",
        "estimand": "dJ = J(a) - J(b), dG = G(a) - G(b) on paired replications",
        "proxy_definition": cfg.versions.proxy_version,
        "metric_definition_version": cfg.versions.metric_version,
        "materiality": {"rule": "m = max(0.01 * |mean J(P0)|, $1,000) on calib (20 reps)",
                        "value_dollars": calib["materiality_dollars"], "mean_J_P0_calib": calib["mean_J_P0"]},
        "equivalence": {"method": "TOST", "alpha": 0.05, "bounds": "+-m"},
        "power": {k: calib[k] for k in ("sd_dJ_P2_P0", "n_req", "n_eval", "capped", "achieved_power", "power_note")},
        "adaptive_extension": False,
        "runtime_budget": {"workers": workers, "K": K, "note": k_note,
                           "per_replication_seconds_calib": calib["per_replication_seconds"]},
        "seeds": cfg.seeds.model_dump(),
        "experiments": {eid: {k: (v if k != "worlds" else {w: o for w, o in v.items()}) for k, v in spec.items()}
                        for eid, spec in cat.items()},
        "E8": {"cells": E8_CELLS, "n": 40, "policies": ["P0", "P2", "P4"], "estimators": ["default M", "M retrained on the cell"]},
        "E9": {"variant_seed": e9_seed, "variants": generate_variants(e9_seed), "n_truth": 100, "n_pilot": 20,
               "pilot_overlay": {"time": {"decision_days": 30, "maturation_days": 60}}, "truth_partition": "eval",
               "pilot_partition": "pilot"},
        "sensitivity": {"seed": sens_seed, "n_points": 48, "reps_per_point": 40, "materiality_reps_per_point": 10,
                        "dims": [list(d) for d in DIMS], "points": latin_hypercube(48, sens_seed),
                        "retrain": {"train_portfolios": 20, "calib_portfolios": 5},
                        "budget_rule": "cut points first if needed, keeping at least 24"},
        "ablations": sorted(ABLATIONS),
        "exclusions": "only prespecified technical-validity failures, with an audit record; all runs reported",
        "classification_order": "INVALID, UNVERIFIED, PROXY_NOT_IMPROVED (proxy contrasts only), REVERSAL/VALUE_LOWER, ALIGNMENT/VALUE_HIGHER, EQUIVALENCE, INCONCLUSIVE",
        "calib_evidence": {k: calib[k] for k in ("n", "mean_dJ_P2_P0", "calib_wall_seconds")},
        "code_commit_at_prereg": code_state()["git_commit"],
    }
    return plan


E8_CELLS = {
    "acc_0.6": {"obs": {"severity_accuracy": 0.6}},
    "acc_1.0": {"obs": {"severity_accuracy": 1.0}},
    "beta_x2": {"retention": {"beta_multiplier": 2.0}},
    "negligence_0.5": {"loss": {"operator_negligence_share": 0.5}},
    "M_275": {"time": {"maturation_days": 275}},
    "speed_quality_+0.6": {"contractors": {"speed_quality_corr": 0.6}},
}


def write_plan(plan: dict[str, Any]) -> str:
    PLAN_PATH.write_text("# MarginBench preregistered plan (machine-readable). Generated by `marginbench prereg`.\n"
                         + yaml.safe_dump(plan, sort_keys=True, width=120))
    (REPO_ROOT / "EXPERIMENT_PLAN.md").write_text(render_plan_md(plan))
    return file_sha256(PLAN_PATH)


def render_plan_md(p: dict[str, Any]) -> str:
    pw = p["power"]
    lines = [
        "# MarginBench experiment plan (v1)",
        "",
        "Generated from `configs/plan.yaml` by `marginbench prereg`. The YAML file is the binding plan; this page restates it.",
        "",
        f"Label: **{p['label']}**. The evaluation is open and preregistered, not blind. Git history proves the ordering:",
        "this plan is committed as `prereg: plan v1` before any locked evaluation runs.",
        "",
        "## Primary contrast",
        "",
        f"- P2 (proxy-planning) against P0 (operating baseline), in the default world, on the `eval` partition, n = {p['primary']['n']} paired replications.",
        "- Estimands: ΔJ (discounted operator contribution, days 30-299) and ΔG (proxy_v1).",
        "- Type: proxy-reversal contrast, unadjusted α = 0.05, two-sided Student-t 95% interval.",
        f"- Materiality m = ${p['materiality']['value_dollars']:,.2f} (max(1% of |mean J(P0)|, $1,000) on 20 calib replications; mean J(P0) = ${p['materiality']['mean_J_P0_calib']:,.2f}).",
        "",
        "## Power",
        "",
        f"- Calib paired SD of ΔJ(P2, P0): ${pw['sd_dJ_P2_P0']:,.2f}. n_req = {pw['n_req']}, n_eval = {pw['n_eval']} (floor 200, cap 2000){' - capped, the primary result may be INCONCLUSIVE' if pw['capped'] else ''}.",
        f"- Achieved power (normal approximation, CI must exclude 0 and the estimate must pass m): {pw['achieved_power']['effect_m']:.3f} at |ΔJ| = m, {pw['achieved_power']['effect_2m']:.3f} at |ΔJ| = 2m.",
        f"- {pw['power_note']}",
        "- No adaptive extension.",
        "",
        "## Confirmatory secondary family (Holm, family α = 0.05)",
        "",
        *[f"- {a} vs {b}" for a, b in p["confirmatory_family"]["contrasts"]],
        "",
        "The k-th smallest p-value gets α = 0.05/(5 − k + 1) and a (1 − α) interval; the sequence stops at the first non-rejection, and that contrast and all later ones cannot be classified directional.",
        "",
        "## Classification",
        "",
        f"Order: {p['classification_order']}. TOST with bounds ±m for equivalence. Run status (VALID/INVALID/UNVERIFIED/RESOURCE_LIMIT) is a separate field.",
        "",
        "## Experiments",
        "",
        "| ID | partition | n | policies | scenarios |",
        "|---|---|---|---|---|",
        *[f"| {eid} | {s['partition']} | {s['n']} | {', '.join(s['policies'])} | {', '.join(s['worlds'])} |" for eid, s in p["experiments"].items()],
        f"| E8 | eval | {p['E8']['n']} | P0, P2, P4 | {', '.join(p['E8']['cells'])} × (default M, retrained M) |",
        f"| E9 | eval (truth, {p['E9']['n_truth']}) + pilot ({p['E9']['n_pilot']}) | - | P1-P5 + 15 seeded variants | default; 30-day pilot |",
        f"| Sensitivity | sens | {p['sensitivity']['materiality_reps_per_point']} + {p['sensitivity']['reps_per_point']} per point | P0, P2, P4 | {p['sensitivity']['n_points']} LHS points |",
        "",
        "## Frozen inputs",
        "",
        f"- Estimator `models/estimator_v1.json` sha256 `{p['estimator']['sha256']}`.",
        f"- Base config hash `{p['base_config']['config_hash']}`; versions {p['versions']}.",
        f"- Seeds: {p['seeds']}.",
        f"- Runtime budget: {p['runtime_budget']['note']}.",
        "",
        "## Exclusions",
        "",
        f"{p['exclusions']}.",
        "",
    ]
    return "\n".join(lines)


class GuardError(RuntimeError):
    pass


def evaluate_guard(plan_path: str) -> dict[str, Any]:
    """Refuses a locked evaluation if the tree is dirty, the plan hash does not match the
    committed file, the estimator hash differs, or any frozen test fails (SPEC 12)."""
    pp = Path(plan_path).resolve()
    if code_state()["dirty"]:
        raise GuardError("working tree is dirty")
    rel = pp.relative_to(REPO_ROOT)
    committed = git("show", f"HEAD:{rel.as_posix()}")
    if not committed:
        raise GuardError("plan is not committed")
    import hashlib

    if hashlib.sha256((committed + "\n").encode()).hexdigest() != file_sha256(pp) and \
            hashlib.sha256(committed.encode()).hexdigest() != file_sha256(pp):
        raise GuardError("plan hash does not match the committed file")
    plan = yaml.safe_load(pp.read_text())
    if file_sha256(EST_PATH) != plan["estimator"]["sha256"]:
        raise GuardError("estimator hash differs from the plan")
    r = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "check_frozen_tests.py")], capture_output=True, text=True)
    if r.returncode != 0:
        raise GuardError("frozen-test hash check failed: " + r.stdout)
    frozen = [l.split(None, 1)[1] for l in (REPO_ROOT / "tests" / "FROZEN.txt").read_text().splitlines()
              if l.strip() and not l.startswith("#") and "/test_" in l]
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", *frozen], cwd=REPO_ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise GuardError("a frozen test fails:\n" + r.stdout[-2000:])
    return {"plan": plan, "plan_hash": file_sha256(pp)}
