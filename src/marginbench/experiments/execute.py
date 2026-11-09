"""Runs one cataloged experiment end to end and writes the SPEC 17.4 artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

from marginbench.config import load_config
from marginbench.estimation.estimator import FrozenEstimator
from marginbench.estimation.perfect import perfect_estimator
from marginbench.evaluation.provenance import code_state, environment_info, utc_now
from marginbench.evaluation.statistics import paired_summary
from marginbench.experiments.pairing import analyze_contrasts, arm_summary, world_status
from marginbench.experiments.partitions import seed_manifest
from marginbench.experiments.runner import make_jobs, replication_job, run_jobs
from marginbench.hashing import canonical_hash, file_sha256, write_json

EXIT = {"VALID": 0, "INVALID": 2, "UNVERIFIED": 3, "RESOURCE_LIMIT": 4}


def _estimator_for(world: str, spec: dict[str, Any], cfg: Any, estimator_path: str, out: Path) -> str:
    kind = spec.get("estimator_overrides", {}).get(world)
    if kind == "perfect":
        p = out / "estimators" / f"perfect_{world}.json"
        perfect_estimator(cfg, FrozenEstimator.load(estimator_path)).save(p)
        return str(p)
    return spec.get("estimator_paths", {}).get(world, estimator_path)


def execute_experiment(exp_id: str, spec: dict[str, Any], estimator_path: str, out_dir: str, m: float,
                       plan_hash: str, workers: int = 4, n_override: Optional[int] = None, rep_offset: int = 0,
                       label: str = "OPEN_PREREGISTERED", base_overlays: Optional[list[dict[str, Any]]] = None,
                       K: Optional[int] = None, H: Optional[int] = None, reproduce_check: bool = True,
                       make_report: bool = True) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    n = n_override if n_override is not None else int(spec["n"])
    reps = list(range(rep_offset, rep_offset + n))
    partition = spec["partition"]
    policies = [{"name": p} for p in spec["policies"]] + list(spec.get("variants", []))
    jobs = []
    configs: dict[str, Any] = {}
    est_paths: dict[str, str] = {}
    for world, overlay in spec["worlds"].items():
        cfg = load_config(overlays=(base_overlays or []) + [overlay])
        configs[world] = cfg
        est_paths[world] = _estimator_for(world, spec, cfg, estimator_path, out)
        jobs += make_jobs(exp_id, world, cfg, est_paths[world], partition, reps, policies,
                          str(out / "traces"), K=K, H=H, deploy=bool(spec.get("deploy", False)))
    max_wall = min(c.limits.max_wall_seconds_per_experiment for c in configs.values())
    results, run_status = run_jobs(jobs, out / "checkpoints", workers=workers, max_wall_seconds=max_wall)

    # --- reproducibility evidence: re-run replication 0 (first world) and compare hashes
    repro: dict[str, Any] = {"status": "NOT_RUN"}
    if reproduce_check and results:
        j0 = jobs[0]
        again = replication_job(dict(j0, trace_dir=None))
        first = next(r for r in results if r["world"] == j0["world"] and r["replication"] == j0["replication"])
        checks = {p: {"event_hash": first["arms"][p]["event_hash"] == again["arms"][p]["event_hash"],
                      "ledger_hash": first["arms"][p]["ledger_hash"] == again["arms"][p]["ledger_hash"]}
                  for p in first["arms"]}
        ok = all(v["event_hash"] and v["ledger_hash"] for v in checks.values())
        repro = {"status": "REPRODUCED" if ok else "MISMATCH", "world": j0["world"], "replication": j0["replication"],
                 "arms": checks}
    verified = repro["status"] == "REPRODUCED"

    # --- statuses
    statuses = {w: world_status(results, w) for w in spec["worlds"]}
    if run_status == "RESOURCE_LIMIT":
        status = "RESOURCE_LIMIT"
    elif any(s == "INVALID" for s in statuses.values()):
        status = "INVALID"
    elif not verified:
        status = "UNVERIFIED"
    else:
        status = "VALID"

    # --- analyses
    analyses: dict[str, Any] = {}
    summaries: dict[str, Any] = {}
    for world in spec["worlds"]:
        analyses[world] = analyze_contrasts(results, world, [tuple(c) for c in spec.get("contrasts", [])], m, exp_id,
                                            primary=tuple(spec["primary"]) if spec.get("primary") else None,
                                            confirmatory=[tuple(c) for c in spec.get("confirmatory", [])] or None,
                                            verified=verified)
        p0J = [r["arms"]["P0"]["J"] for r in results if r["world"] == world and "P0" in r["arms"]]
        q05 = float(np.quantile(p0J, 0.05)) if p0J else None
        summaries[world] = {p["name"]: arm_summary(results, world, p["name"], q05, seed=4242) for p in policies}
        feas = {p: s["J"]["mean"] for p, s in summaries[world].items() if p != "P6" and s["n"]}
        if feas:
            best = max(feas, key=lambda p: (feas[p], p))
            analyses[world]["gap_to_best_evaluated_policy"] = {
                "label": "gap to best evaluated policy (not regret: the optimum is not computed)",
                "best_evaluated_policy": best,
                "gaps_dollars": {p: feas[best] - v for p, v in sorted(feas.items())},
                "excluded": ["P6 (NON-DEPLOYABLE DIAGNOSTIC)"] if any(p["name"] == "P6" for p in policies) else []}
    cross: dict[str, Any] = {}
    ref = spec.get("reference")
    if ref:
        for world in spec["worlds"]:
            if world == ref:
                continue
            cross[world] = {}
            for a, b in spec.get("contrasts", []):
                d = []
                for r in results:
                    if r["world"] != world:
                        continue
                    rr = next((x for x in results if x["world"] == ref and x["replication"] == r["replication"]), None)
                    if rr is None or a not in r["arms"] or b not in r["arms"]:
                        continue
                    d.append((r["arms"][a]["J"] - r["arms"][b]["J"]) - (rr["arms"][a]["J"] - rr["arms"][b]["J"]))
                cross[world][f"{a}-{b}"] = {"label": "EXPLORATORY: change in dJ relative to the reference world, paired by replication",
                                            "reference": ref, **paired_summary(d).to_dict()}

    # --- artifacts
    est_hashes = {w: file_sha256(p) for w, p in est_paths.items()}
    run_id = f"{exp_id}-{canonical_hash({'c': {w: c.config_hash() for w, c in configs.items()}, 'e': est_hashes, 'p': plan_hash, 'n': n, 'o': rep_offset})[:12]}"
    code = code_state()
    manifest = {
        "run_id": run_id,
        "experiment": exp_id,
        "label": label,
        "utc_started": started,
        "utc_finished": utc_now(),
        "git_commit": code["git_commit"],
        "git_dirty": code["dirty"],
        **environment_info(),
        "sim_version": next(iter(configs.values())).versions.sim_version,
        "policy_version": next(iter(configs.values())).versions.policy_version,
        "metric_definition_version": next(iter(configs.values())).versions.metric_version,
        "proxy_version": next(iter(configs.values())).versions.proxy_version,
        "random_stream_schema": next(iter(configs.values())).versions.stream_schema,
        "config_hashes": {w: c.config_hash() for w, c in configs.items()},
        "estimator_hashes": est_hashes,
        "plan_hash": plan_hash,
        "partition": partition,
        "n_replications": n,
        "replication_offset": rep_offset,
        "seed_manifest": seed_manifest(next(iter(configs.values())), partition, reps),
        "policies": [p["name"] for p in policies],
        "K_override": K,
        "H_override": H,
        "materiality_dollars": m,
        "run_status": status,
        "world_status": statuses,
        "reproducibility_status": repro["status"],
        "hash_excluded_fields": ["utc_started", "utc_finished"],
    }
    write_json(out / "run_manifest.json", manifest)
    write_json(out / "config.json", {w: c.model_dump(mode="json") for w, c in configs.items()})
    (out / "plan_hash.txt").write_text(plan_hash + "\n")
    write_json(out / "policy_manifest.json", {
        "policies": policies, "feasible": [p["name"] for p in policies if p["name"] != "P6"],
        "non_deployable": [p["name"] for p in policies if p["name"] == "P6"],
        "K": K or next(iter(configs.values())).planning.K, "H_plan_days": H or next(iter(configs.values())).planning.H_plan_days,
        "policy_version": next(iter(configs.values())).versions.policy_version,
        "matched_pairs": [["P1", "P3"], ["P2", "P4"], ["P4", "P5"]]})
    write_json(out / "estimator_manifest.json", {"estimator_paths": est_paths, "estimator_hashes": est_hashes,
                                                  "labels": {w: ("PERFECT-ESTIMATOR DIAGNOSTIC" if "perfect" in p else "estimator_v1")
                                                             for w, p in est_paths.items()}})
    write_json(out / "metrics.json", {"run_id": run_id, "materiality_dollars": m, "analyses": analyses,
                                      "arm_summaries": summaries, "cross_world": cross, "units": {"J": "USD", "G": "proxy_v1 (dimensionless)"}})
    rows = []
    for world, an in analyses.items():
        for a, b in [tuple(c) for c in spec.get("contrasts", [])]:
            for r in results:
                if r["world"] != world or a not in r["arms"] or b not in r["arms"]:
                    continue
                A, B = r["arms"][a], r["arms"][b]
                rows.append({"run_id": run_id, "experiment": exp_id, "world": world, "replication": r["replication"],
                             "contrast": f"{a}-{b}", "a": a, "b": b, "J_a": A["J"], "J_b": B["J"], "dJ": A["J"] - B["J"],
                             "G_a": A["G"], "G_b": B["G"],
                             "dG": (A["G"] - B["G"]) if A["G"] is not None and B["G"] is not None else None,
                             "status_a": A["status"], "status_b": B["status"]})
    with open(out / "paired_results.csv", "w", newline="") as fh:
        cols = ["run_id", "experiment", "world", "replication", "contrast", "a", "b", "J_a", "J_b", "dJ", "G_a", "G_b",
                "dG", "status_a", "status_b"]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if row[k] is None else row[k]) for k in cols})
    with open(out / "replications.jsonl", "w") as fh:
        for r in results:
            slim = {"world": r["world"], "replication": r["replication"], "arms": {
                p: {k: v for k, v in a.items() if k not in ("diagnostics",)} for p, a in r["arms"].items()}}
            fh.write(json.dumps(slim, sort_keys=True) + "\n")
    write_json(out / "boundary.json", {w: {p: _mean_boundary([r["arms"][p]["boundary"] for r in results
                                                              if r["world"] == w and p in r["arms"]])
                                           for p in [x["name"] for x in policies]} for w in spec["worlds"]})
    write_json(out / "policy_diagnostics.json", {w: {p: summaries[w][p].get("compute") for p in summaries[w]}
                                                 for w in summaries})
    validation = {"run_status": status, "world_status": statuses, "reproducibility": repro,
                  "errors": [{"world": r["world"], "replication": r["replication"], "policy": p,
                              "reconciliation": a["reconciliation_errors"], "transitions": a["transition_errors"],
                              "engine": a["engine_validation_errors"]}
                             for r in results for p, a in r["arms"].items()
                             if a["reconciliation_errors"] or a["transition_errors"] or a["engine_validation_errors"]],
                  "replications_completed": len(results), "replications_planned": len(jobs),
                  "exclusions": []}
    write_json(out / "validation.json", validation)
    series = {r["world"] + "|" + str(r["replication"]): r["series"] for r in results if r.get("series")}
    write_json(out / "series.json", series)
    from marginbench.reporting.claims import build_claim_audit

    claim_audit = build_claim_audit(run_id, exp_id, spec, analyses, cross, out, label)
    write_json(out / "claim_audit.json", claim_audit)
    if make_report:
        from marginbench.reporting.html import build_report

        build_report(out)
    return {"run_id": run_id, "status": status, "exit_code": EXIT[status], "out": str(out),
            "reproducibility": repro["status"]}


def _mean_boundary(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {}
    keys = [k for k, v in items[0].items() if isinstance(v, (int, float))]
    return {"label": "ESTIMATES - excluded from J (SPEC 6.4); means over replications",
            **{k: float(np.mean([it[k] for it in items])) for k in keys}}
