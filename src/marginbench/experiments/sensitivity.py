"""Sensitivity design (SPEC 15): seeded Latin hypercube over 14 dimensions. Each point
retrains M on training portfolios generated under that point's parameters, then runs P0,
P2 and P4. Materiality per point comes from that point's first 10 replications, which are
excluded from inference. Shares are shares of tested design points, never real-world
probabilities."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np
from scipy import stats

from marginbench.config import load_config
from marginbench.evaluation.classification import PROXY_REVERSAL, VALUE, evaluate_contrast
from marginbench.evaluation.statistics import materiality
from marginbench.hashing import write_json

DIMS: list[tuple[str, float, float]] = [
    ("success_dispersion", 0.0, 2.0),
    ("speed_quality_corr", -0.6, 0.6),
    ("price_quality_corr", -0.6, 0.6),
    ("m_sev_scale", 0.5, 1.2),
    ("report_delay_scale_days", 2.0, 10.0),
    ("m_close", 0.6, 1.0),
    ("verification_cost", 5.0, 60.0),
    ("verification_sensitivity", 0.6, 1.0),
    ("beta_multiplier", 0.0, 3.0),
    ("capacity_multiplier", 0.5, 2.0),
    ("arrival_rate_multiplier", 0.5, 2.0),
    ("severe_hazard_multiplier", 0.0, 5.0),
    ("H_plan_days", 15.0, 90.0),
    ("discount_rate", 0.0, 0.20),
]


def latin_hypercube(n: int, seed: int) -> list[dict[str, float]]:
    g = np.random.Generator(np.random.PCG64DXSM(seed))
    d = len(DIMS)
    u = np.empty((n, d))
    for j in range(d):
        perm = g.permutation(n)
        u[:, j] = (perm + g.random(n)) / n
    pts = []
    for i in range(n):
        p = {}
        for j, (name, lo, hi) in enumerate(DIMS):
            v = lo + u[i, j] * (hi - lo)
            p[name] = float(round(v)) if name == "H_plan_days" else float(v)
        pts.append(p)
    return pts


def overlay_for(p: dict[str, float]) -> dict[str, Any]:
    return {
        "contractors": {"success_dispersion": p["success_dispersion"], "speed_quality_corr": p["speed_quality_corr"],
                        "price_quality_corr": p["price_quality_corr"], "capacity_multiplier": p["capacity_multiplier"]},
        "callbacks": {"m_sev_scale": p["m_sev_scale"], "delay_gamma_scale_days": p["report_delay_scale_days"],
                      "m_close_unverified": p["m_close"]},
        "verify": {"cost": p["verification_cost"], "sensitivity": p["verification_sensitivity"]},
        "retention": {"beta_multiplier": p["beta_multiplier"]},
        "arrivals": {"rate_multiplier": p["arrival_rate_multiplier"]},
        "loss": {"hazard_multiplier": p["severe_hazard_multiplier"]},
        "planning": {"H_plan_days": int(p["H_plan_days"])},
        "time": {"annual_discount_rate": p["discount_rate"]},
    }


def run_sensitivity(out_dir: str, plan_hash: str, seed: int, n_points: int = 48, reps_per_point: int = 40,
                    m_reps: int = 10, n_train: int = 20, n_calib: int = 5, workers: int = 4,
                    points: Optional[list[int]] = None) -> dict[str, Any]:
    from marginbench.estimation.training import train_and_freeze
    from marginbench.experiments.execute import execute_experiment

    out = Path(out_dir)
    pts = latin_hypercube(n_points, seed)
    rows = []
    for i, p in enumerate(pts):
        if points is not None and i not in points:
            continue
        pdir = out / f"point_{i:02d}"
        overlay = overlay_for(p)
        cfg = load_config(overlays=[overlay])
        est_path = pdir / "estimator.json"
        if not est_path.exists():
            # train/calib histories for this point use the 'sens' partition, replications
            # offset far from the evaluation replications of every point
            ov = [overlay, {"seeds": {"train": cfg.seeds.sens + 100_000 + i, "calib": cfg.seeds.sens + 200_000 + i}}]
            train_and_freeze(load_config(overlays=ov), str(est_path), str(pdir / "estimator_audit.json"),
                             n_train=n_train, n_calib=n_calib, workers=workers)
        spec = {"partition": "sens", "n": m_reps + reps_per_point, "policies": ["P0", "P2", "P4"],
                "worlds": {f"point_{i:02d}": overlay}, "contrasts": [("P2", "P0"), ("P4", "P2")]}
        execute_experiment(f"SENS-{i:02d}", spec, str(est_path), str(pdir / "run"), m=1000.0, plan_hash=plan_hash,
                           workers=workers, rep_offset=i * 1000, reproduce_check=True, make_report=False)
        reps = [json.loads(x) for x in (pdir / "run" / "replications.jsonl").read_text().splitlines()]
        reps.sort(key=lambda r: r["replication"])
        first, rest = reps[:m_reps], reps[m_reps:]
        m = materiality(float(np.mean([r["arms"]["P0"]["J"] for r in first])))
        res = {}
        for a, b, kind in (("P2", "P0", PROXY_REVERSAL), ("P4", "P2", VALUE)):
            dj = [r["arms"][a]["J"] - r["arms"][b]["J"] for r in rest]
            dg = [r["arms"][a]["G"] - r["arms"][b]["G"] for r in rest
                  if r["arms"][a]["G"] is not None and r["arms"][b]["G"] is not None]
            res[(a, b)] = evaluate_contrast(a, b, kind, dj, dg, m)
        status = json.loads((pdir / "run" / "run_manifest.json").read_text())["run_status"]
        r20, r42 = res[("P2", "P0")], res[("P4", "P2")]
        row = {"point": i, **p, "materiality": m, "n_inference": len(rest), "run_status": status,
               "dJ_P2_P0": r20.dJ["mean"], "dJ_P2_P0_ci_low": r20.dJ["ci_low"], "dJ_P2_P0_ci_high": r20.dJ["ci_high"],
               "dG_P2_P0": r20.dG.get("mean"), "dG_P2_P0_ci_low": r20.dG.get("ci_low"), "dG_P2_P0_ci_high": r20.dG.get("ci_high"),
               "class_P2_P0": r20.classification, "strong_P2_P0": r20.strong,
               "dJ_P4_P2": r42.dJ["mean"], "dJ_P4_P2_ci_low": r42.dJ["ci_low"], "dJ_P4_P2_ci_high": r42.dJ["ci_high"],
               "class_P4_P2": r42.classification}
        rows.append(row)
        write_json(pdir / "point_result.json", row)
    summarize_sensitivity(out, rows)
    return {"points": len(rows)}


def summarize_sensitivity(out: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    cols = list(rows[0].keys())
    with open(out / "sensitivity.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    rho = {}
    z = np.array([r["dJ_P2_P0"] for r in rows])
    for name, _, _ in DIMS:
        x = np.array([r[name] for r in rows])
        rho[name] = float(stats.spearmanr(x, z).statistic) if len(rows) > 2 and np.std(x) > 0 else None
    top = sorted([k for k in rho if rho[k] is not None], key=lambda k: -abs(rho[k]))[:2]
    shares = {}
    for key in ("class_P2_P0", "class_P4_P2"):
        cnt: dict[str, int] = {}
        for r in rows:
            cnt[r[key]] = cnt.get(r[key], 0) + 1
        shares[key] = {k: {"count": v, "share_of_tested_design_points": v / len(rows)} for k, v in sorted(cnt.items())}
    summary = {"label": "shares are shares of TESTED DESIGN POINTS, not real-world probabilities",
               "n_points": len(rows), "spearman_rho_vs_dJ_P2_P0": rho, "top_dimensions": top, "class_shares": shares}
    write_json(out / "sensitivity_summary.json", summary)
    from marginbench.reporting.charts import sensitivity_panels

    if len(top) == 2:
        sensitivity_panels(rows, top, out / "sensitivity_panel.png",
                           f"sensitivity design · {len(rows)} tested points · seed-locked LHS")
    return summary
