"""Experiment runner (SPEC 13, 17): paired replications, checkpoints, resume, parallelism.

A replication job builds the keyed world once and runs every policy arm on it. P0 makes
warm-up and continuation decisions in every arm. Results are byte-identical whether jobs
run serially or in a process pool (tests/integration/test_parallel.py).
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Optional

from marginbench.config import Config, config_from_dict, public_config
from marginbench.economics.reconciliation import reconcile
from marginbench.environment.arrivals import build_world
from marginbench.environment.engine import Engine, RunSpec
from marginbench.environment.randomness import StreamFactory, run_nonce
from marginbench.estimation.estimator import FrozenEstimator
from marginbench.evaluation.metrics import compute_metrics, daily_series
from marginbench.evaluation.validation import validate_transitions
from marginbench.hashing import canonical_hash, file_sha256, write_json, write_jsonl
from marginbench.policies.runner import make_policy

TRACE_REPS = 3
SERIES_REPS = 3

_EST_CACHE: dict[str, FrozenEstimator] = {}


def _estimator(path: str) -> FrozenEstimator:
    if path not in _EST_CACHE:
        _EST_CACHE[path] = FrozenEstimator.load(path)
    return _EST_CACHE[path]


def run_arm(cfg: Config, world: Any, est: FrozenEstimator, policy_name: str, partition: str, rep: int,
            run_id: str, K: Optional[int] = None, H: Optional[int] = None, variant: Optional[dict[str, Any]] = None,
            deploy: bool = False, privileged: Any = None) -> tuple[Any, Any]:
    pub = public_config(cfg)
    p0 = make_policy("P0")
    p0.reset(pub, est, None)
    if policy_name == "P0" and variant is None:
        arm = p0
    else:
        arm = make_policy(policy_name, K=K, H_plan_days=H, variant=variant)
        arm.reset(pub, est, None)
        if privileged is not None and hasattr(arm, "attach_privileged"):
            arm.attach_privileged(privileged)
    spec = RunSpec(run_id, cfg.time.horizon_days, run_nonce(cfg.seeds.nonce_key, partition, rep), mode="eval",
                   deploy_variant=deploy or cfg.time.deploy_variant, max_events=cfg.limits.max_events_per_replication)
    eng = Engine(cfg, world, spec, arm, p0)
    if privileged is not None and hasattr(arm, "attach_engine_truth"):
        arm.attach_engine_truth(eng)
    out = eng.run()
    return eng, out


def replication_job(job: dict[str, Any]) -> dict[str, Any]:
    """One replication of one world: every arm on the same keyed world."""
    cfg = config_from_dict(job["config"])
    est = _estimator(job["estimator_path"])
    partition, rep = job["partition"], int(job["replication"])
    sf = StreamFactory(cfg.versions.sim_version, partition, cfg.seeds.master(partition), rep)
    world = build_world(cfg, sf, cfg.time.horizon_days)
    arms: dict[str, Any] = {}
    series: dict[str, Any] = {}
    for pol in job["policies"]:
        name = pol["name"]
        run_id = f"{job['experiment']}|{job['world']}|{partition}|{rep}|{name}"
        t0 = time.perf_counter()
        eng, out = run_arm(cfg, world, est, name, partition, rep, run_id, K=job.get("K"),
                           H=job.get("H"), variant=pol.get("variant"), deploy=job.get("deploy", False),
                           privileged=(world if name == "P6" else None))
        cids = sorted(out.contracts)
        cp = {k: v.property_id for k, v in out.contracts.items()}
        rec_errors = reconcile(out.events, out.ledger.entries, cfg, out.run_id, cids, cp, eng.end_tick)
        tr_errors = validate_transitions(out.events)
        status = out.status
        if status == "VALID" and (rec_errors or tr_errors):
            status = "INVALID"
        m = compute_metrics(out, cfg, cfg.time.horizon_days)
        arms[name] = {
            "status": status,
            "J": m["J_dollars"],
            "G": m["G"],
            "metrics": m,
            "event_hash": out.event_hash,
            "ledger_hash": out.ledger_hash,
            "reconciliation_errors": rec_errors[:20],
            "transition_errors": tr_errors[:20],
            "engine_validation_errors": out.validation_errors[:20],
            "decisions_by_policy": out.decisions_by_policy,
            "diagnostics": out.policy_diagnostics,
            "boundary": out.boundary,
            "wall_seconds": round(time.perf_counter() - t0, 3),
            "n_events": len(out.events),
            "n_ledger_entries": len(out.ledger.entries),
            "ledger_totals": {f"{p}|{c}": v for (p, c), v in sorted(out.ledger.totals_by_principal_category().items())},
        }
        if rep < SERIES_REPS:
            series[name] = daily_series(out, cfg, cfg.time.horizon_days)
        if job.get("trace_dir") and rep < TRACE_REPS:
            d = Path(job["trace_dir"]) / job["world"] / f"rep_{rep:04d}" / name
            write_jsonl(d / "events.jsonl", [e.to_record() for e in out.events])
            write_jsonl(d / "actions.jsonl", out.action_records)
            write_jsonl(d / "ledger.jsonl", [e.to_record() for e in out.ledger.entries])
    return {"experiment": job["experiment"], "world": job["world"], "partition": partition, "replication": rep,
            "arms": arms, "series": series, "job_hash": job["job_hash"]}


def make_jobs(experiment: str, world: str, cfg: Config, estimator_path: str, partition: str, reps: list[int],
              policies: list[dict[str, Any]], trace_dir: Optional[str], K: Optional[int] = None,
              H: Optional[int] = None, deploy: bool = False) -> list[dict[str, Any]]:
    cfg_json = cfg.model_dump(mode="json")
    est_hash = file_sha256(estimator_path)
    base = {"experiment": experiment, "world": world, "config": cfg_json, "estimator_path": estimator_path,
            "partition": partition, "policies": policies, "K": K, "H": H, "deploy": deploy, "trace_dir": trace_dir}
    jh = canonical_hash({"config_hash": cfg.config_hash(), "estimator_hash": est_hash, "partition": partition,
                         "policies": policies, "K": K, "H": H, "deploy": deploy, "experiment": experiment, "world": world})
    return [{**base, "replication": r, "job_hash": jh} for r in reps]


def run_jobs(jobs: list[dict[str, Any]], checkpoint_dir: Optional[Path], workers: int = 4,
             max_wall_seconds: Optional[float] = None) -> tuple[list[dict[str, Any]], str]:
    """Runs jobs with atomic per-replication checkpoints and resume. Returns (results in job
    order, status). Refuses to merge a checkpoint whose job hash differs."""
    results: dict[int, dict[str, Any]] = {}
    todo = []
    for i, j in enumerate(jobs):
        cp = checkpoint_dir / f"{j['world']}__rep_{j['replication']:05d}.json" if checkpoint_dir else None
        if cp is not None and cp.exists():
            data = json.loads(cp.read_text())
            if data.get("job_hash") != j["job_hash"]:
                raise RuntimeError(f"checkpoint {cp} has a different manifest hash; refusing to merge")
            results[i] = data
        else:
            todo.append((i, j, cp))
    t0 = time.perf_counter()
    status = "VALID"

    def store(i: int, cp: Optional[Path], res: dict[str, Any]) -> None:
        results[i] = res
        if cp is not None:
            write_json(cp, res)

    if workers <= 1 or len(todo) <= 1:
        for i, j, cp in todo:
            if max_wall_seconds and time.perf_counter() - t0 > max_wall_seconds:
                status = "RESOURCE_LIMIT"
                break
            store(i, cp, replication_job(j))
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [(i, cp, ex.submit(replication_job, j)) for i, j, cp in todo]
            for i, cp, f in futs:
                remaining = None
                if max_wall_seconds:
                    remaining = max(1.0, max_wall_seconds - (time.perf_counter() - t0))
                try:
                    store(i, cp, f.result(timeout=remaining))
                except TimeoutError:
                    status = "RESOURCE_LIMIT"
                    for _, _, g in futs:
                        g.cancel()
                    break
    ordered = [results[i] for i in sorted(results)]
    if len(ordered) < len(jobs) and status == "VALID":
        status = "RESOURCE_LIMIT"
    return ordered, status
