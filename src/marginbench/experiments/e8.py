"""E8 misspecification (SPEC 13): M trained on the default world, evaluated in extreme
cells, compared with M retrained on each cell (out-of-distribution performance)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marginbench.config import load_config
from marginbench.hashing import write_json


def run_e8(estimator_path: str, out_dir: str, m: float, plan_hash: str, cells: dict[str, Any], n: int = 40,
           workers: int = 4) -> dict[str, Any]:
    from marginbench.estimation.estimator import FrozenEstimator
    from marginbench.estimation.training import train_and_freeze
    from marginbench.experiments.execute import execute_experiment

    out = Path(out_dir)
    worlds: dict[str, Any] = {}
    est_paths: dict[str, str] = {}
    params_cmp: dict[str, Any] = {}
    base = FrozenEstimator.load(estimator_path)
    for i, (cell, overlay) in enumerate(cells.items()):
        cfg = load_config(overlays=[overlay])
        ep = out / "estimators" / f"{cell}.json"
        if not ep.exists():
            ov = [overlay, {"seeds": {"train": cfg.seeds.train + 300_000 + i, "calib": cfg.seeds.calib + 300_000 + i}}]
            train_and_freeze(load_config(overlays=ov), str(ep), str(out / "estimators" / f"{cell}_audit.json"),
                             n_train=20, n_calib=5, workers=workers)
        worlds[f"{cell}|default_M"] = overlay
        worlds[f"{cell}|retrained_M"] = overlay
        est_paths[f"{cell}|retrained_M"] = str(ep)
        re = FrozenEstimator.load(ep)
        params_cmp[cell] = {"default_M": {k: base.params["report_verify"][k] for k in ("tc", "fc", "sens", "spec")},
                            "retrained_M": {k: re.params["report_verify"][k] for k in ("tc", "fc", "sens", "spec")},
                            "termination_coef": {"default_M": base.params["termination"]["coef"],
                                                 "retrained_M": re.params["termination"]["coef"]}}
    spec = {"partition": "eval", "n": n, "policies": ["P0", "P2", "P4"], "worlds": worlds,
            "contrasts": [("P2", "P0"), ("P4", "P2"), ("P4", "P0")], "estimator_paths": est_paths}
    r = execute_experiment("E8", spec, estimator_path, str(out / "run"), m, plan_hash, workers=workers)
    met = json.loads((out / "run" / "metrics.json").read_text())
    ood = {}
    for cell in cells:
        a = met["analyses"][f"{cell}|default_M"]["contrasts"]
        b = met["analyses"][f"{cell}|retrained_M"]["contrasts"]
        ood[cell] = {k: {"default_M": {"class": a[k]["classification"], "dJ": a[k]["dJ"]["mean"]},
                         "retrained_M": {"class": b[k]["classification"], "dJ": b[k]["dJ"]["mean"]}} for k in a}
    res = {"status": r["status"], "run": r, "out_of_distribution": ood, "estimator_parameters": params_cmp}
    write_json(out / "e8_results.json", res)
    return res
