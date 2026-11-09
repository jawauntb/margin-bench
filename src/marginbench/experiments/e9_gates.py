"""E9: evaluation-method comparison (SPEC 13). Four pilot gates are compared with ground
truth from full-horizon replications."""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import Any

import numpy as np

from marginbench.evaluation.classification import VALUE, evaluate_contrast
from marginbench.evaluation.statistics import paired_summary
from marginbench.hashing import write_json

PILOT_OVERLAY = {"time": {"decision_days": 30, "maturation_days": 60}}
BASE_CANDIDATES = ["P1", "P2", "P3", "P4", "P5"]


def variant_grid() -> list[dict[str, Any]]:
    out = []
    for obj, H, tau, vb in itertools.product(("proxy", "econ"), (0, 15, 30), (None, 0.1, 0.3), ("none", "low", "high")):
        bonus = {"none": 0.0, "low": 0.1 if obj == "proxy" else 5.0, "high": 0.3 if obj == "proxy" else 15.0}[vb]
        out.append({"objective": obj, "H_plan_days": H, "close_tau": tau, "verify_bonus": bonus})
    return out


def generate_variants(seed: int, n: int = 15) -> list[dict[str, Any]]:
    """Seeded rule: sample n distinct grid cells without replacement (plan records the seed)."""
    grid = variant_grid()
    g = np.random.Generator(np.random.PCG64DXSM(seed))
    idx = sorted(int(i) for i in g.choice(len(grid), size=n, replace=False))
    return [{"name": f"V{k + 1:02d}", "variant": grid[i]} for k, i in enumerate(idx)]


def wilson(k: int, n: int, z: float = 1.959964) -> list[float | None]:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def truth_classes(results: list[dict[str, Any]], candidates: list[str], m: float) -> dict[str, Any]:
    out = {}
    for c in candidates:
        dj = [r["arms"][c]["J"] - r["arms"]["P0"]["J"] for r in results
              if c in r["arms"] and r["arms"][c]["status"] == "VALID" and r["arms"]["P0"]["status"] == "VALID"]
        res = evaluate_contrast(c, "P0", VALUE, dj, [], m)
        out[c] = {"classification": res.classification, "dJ": res.dJ}
    return out


def gate_decisions(pilot: list[dict[str, Any]], candidates: list[str]) -> dict[str, Any]:
    out = {}
    for c in candidates:
        rows = [r for r in pilot if c in r["arms"]]
        dG = [r["arms"][c]["G"] - r["arms"]["P0"]["G"] for r in rows
              if r["arms"][c]["G"] is not None and r["arms"]["P0"]["G"] is not None]
        dV = [(r["arms"][c]["metrics"]["verified_resolution_rate"] or 0.0) - (r["arms"]["P0"]["metrics"]["verified_resolution_rate"] or 0.0)
              for r in rows if r["arms"][c]["metrics"]["verified_resolution_rate"] is not None
              and r["arms"]["P0"]["metrics"]["verified_resolution_rate"] is not None]
        dJ = [r["arms"][c]["J"] - r["arms"]["P0"]["J"] for r in rows]
        sG, sV, sJ = paired_summary(dG), paired_summary(dV), paired_summary(dJ)
        loss_c = float(np.mean([r["arms"][c]["metrics"]["severe_loss_count"] for r in rows])) if rows else 0.0
        loss_0 = float(np.mean([r["arms"]["P0"]["metrics"]["severe_loss_count"] for r in rows])) if rows else 0.0
        br_c = float(np.mean([r["arms"][c]["metrics"]["sla_breach_count"] for r in rows])) if rows else 0.0
        br_0 = float(np.mean([r["arms"]["P0"]["metrics"]["sla_breach_count"] for r in rows])) if rows else 0.0
        a = bool(sG.ci_low is not None and sG.ci_low > 0)
        b = bool(sV.ci_low is not None and sV.ci_low > 0)
        cg = bool(sJ.ci_low is not None and sJ.ci_low > 0)
        d = bool(cg and loss_c <= 1.10 * loss_0 + 1e-12 and br_c <= 1.10 * br_0 + 1e-12)
        out[c] = {"proxy_gate": a, "verified_gate": b, "value_gate": cg, "risk_gate": d,
                  "dG": sG.to_dict(), "dVerified": sV.to_dict(), "dJ_pilot": sJ.to_dict(),
                  "severe_loss_mean": [loss_c, loss_0], "sla_breach_mean": [br_c, br_0]}
    return out


def gate_table(truth: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    classes = ["VALUE_HIGHER_SUPPORTED", "VALUE_LOWER_SUPPORTED", "EQUIVALENCE_SUPPORTED", "INCONCLUSIVE"]
    table = {}
    for gname in ("proxy_gate", "verified_gate", "value_gate", "risk_gate"):
        conf = {cl: {"approved": 0, "rejected": 0} for cl in classes}
        for c, t in truth.items():
            cl = t["classification"] if t["classification"] in conf else "INCONCLUSIVE"
            conf[cl]["approved" if gates[c][gname] else "rejected"] += 1
        pos_n = sum(conf["VALUE_HIGHER_SUPPORTED"].values())
        neg_n = sum(sum(v.values()) for k, v in conf.items() if k != "VALUE_HIGHER_SUPPORTED")
        fa = sum(v["approved"] for k, v in conf.items() if k != "VALUE_HIGHER_SUPPORTED")
        fr = conf["VALUE_HIGHER_SUPPORTED"]["rejected"]
        harm_n = sum(conf["VALUE_LOWER_SUPPORTED"].values())
        table[gname] = {
            "confusion": conf,
            "false_approval_rate": (fa / neg_n) if neg_n else None, "false_approval_wilson95": wilson(fa, neg_n),
            "false_rejection_rate": (fr / pos_n) if pos_n else None, "false_rejection_wilson95": wilson(fr, pos_n),
            "harmful_approval_rate": (conf["VALUE_LOWER_SUPPORTED"]["approved"] / harm_n) if harm_n else None,
            "harmful_approval_wilson95": wilson(conf["VALUE_LOWER_SUPPORTED"]["approved"], harm_n),
            "n_positive_truth": pos_n, "n_negative_truth": neg_n,
            "definition": "positive truth = ΔJ(c, P0) classified VALUE_HIGHER_SUPPORTED on 100 eval replications",
        }
    return table


def run_e9(estimator_path: str, out_dir: str, m: float, plan_hash: str, variant_seed: int, n_truth: int = 100,
           n_pilot: int = 20, workers: int = 4) -> dict[str, Any]:
    from marginbench.experiments.execute import execute_experiment

    out = Path(out_dir)
    variants = generate_variants(variant_seed)
    cands = BASE_CANDIDATES + [v["name"] for v in variants]
    truth_spec = {"partition": "eval", "n": n_truth, "policies": ["P0"] + BASE_CANDIDATES, "variants": variants,
                  "worlds": {"default": {}}, "contrasts": [(c, "P0") for c in cands]}
    r1 = execute_experiment("E9-truth", truth_spec, estimator_path, str(out / "truth"), m, plan_hash, workers=workers)
    pilot_spec = {"partition": "pilot", "n": n_pilot, "policies": ["P0"] + BASE_CANDIDATES, "variants": variants,
                  "worlds": {"pilot": PILOT_OVERLAY}, "contrasts": [(c, "P0") for c in cands]}
    r2 = execute_experiment("E9-pilot", pilot_spec, estimator_path, str(out / "pilot"), m, plan_hash, workers=workers)
    import json

    truth_res = [json.loads(x) for x in (out / "truth" / "replications.jsonl").read_text().splitlines()]
    pilot_res = [json.loads(x) for x in (out / "pilot" / "replications.jsonl").read_text().splitlines()]
    truth = truth_classes(truth_res, cands, m)
    gates = gate_decisions(pilot_res, cands)
    table = gate_table(truth, gates)
    status = "VALID" if r1["status"] == "VALID" and r2["status"] == "VALID" else (
        "INVALID" if "INVALID" in (r1["status"], r2["status"]) else r1["status"] if r1["status"] != "VALID" else r2["status"])
    res = {"label": "E9 evaluation-method comparison (OPEN_PREREGISTERED)", "status": status,
           "truth_run": r1, "pilot_run": r2, "variants": variants, "truth": truth, "gates": gates, "table": table,
           "materiality": m, "pilot_overlay": PILOT_OVERLAY}
    write_json(out / "e9_results.json", res)
    return res
