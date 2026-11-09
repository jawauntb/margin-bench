"""MarginBench command line (SPEC 17.3). Exit codes: 0 valid run (whatever the scientific
result), 2 INVALID, 3 UNVERIFIED, 4 RESOURCE_LIMIT."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer
import yaml

from marginbench.config import REPO_ROOT, load_config

app = typer.Typer(add_completion=False, help="MarginBench: proxy vs long-horizon value benchmark")
EXIT = {"VALID": 0, "INVALID": 2, "UNVERIFIED": 3, "RESOURCE_LIMIT": 4}
EST = str(REPO_ROOT / "models" / "estimator_v1.json")
PLAN = str(REPO_ROOT / "configs" / "plan.yaml")


def _load_plan(plan: str, guard: bool) -> tuple[dict, str]:
    from marginbench.experiments.prereg import GuardError, evaluate_guard
    from marginbench.hashing import file_sha256

    if guard:
        try:
            g = evaluate_guard(plan)
        except GuardError as e:
            typer.echo(f"REFUSED: {e}", err=True)
            raise typer.Exit(3)
        return g["plan"], g["plan_hash"]
    return yaml.safe_load(Path(plan).read_text()), file_sha256(plan)


@app.command()
def validate(config: str = typer.Option("configs/default.yaml", "--config")) -> None:
    """Validate a config and the observation allowlist."""
    from marginbench.environment.observations import validate_allowlist
    from marginbench.environment.state import check_visibility_registry

    cfg = load_config(config)
    check_visibility_registry()
    validate_allowlist()
    typer.echo(json.dumps({"config": config, "config_hash": cfg.config_hash(), "valid": True}))


@app.command()
def smoke(config: str = typer.Option("configs/default.yaml", "--config"), workers: int = 4) -> None:
    """One dev replication of every policy; reconciliation; runtime projection."""
    from marginbench.experiments.runner import make_jobs, replication_job

    cfg = load_config(config)
    jobs = make_jobs("SMOKE", "default", cfg, EST, "dev", [0], [{"name": p} for p in ("P0", "P1", "P2", "P3", "P4", "P5")],
                     trace_dir=None)
    t0 = time.perf_counter()
    r = replication_job(jobs[0])
    wall = time.perf_counter() - t0
    status = "VALID" if all(a["status"] == "VALID" for a in r["arms"].values()) else "INVALID"
    proj = 200 * wall / max(workers, 1)
    out = {"status": status, "wall_seconds": round(wall, 2), "projected_primary_hours_at_n200": round(proj / 3600, 3),
           "arms": {p: {"status": a["status"], "J": a["J"], "G": a["G"], "seconds": a["wall_seconds"],
                        "reconciliation_errors": len(a["reconciliation_errors"])} for p, a in r["arms"].items()}}
    typer.echo(json.dumps(out, indent=1))
    raise typer.Exit(EXIT[status])


@app.command()
def train(config: str = typer.Option("configs/default.yaml", "--config"), workers: int = 4) -> None:
    """Generate history, fit and freeze the estimator M (models/estimator_v1.json)."""
    from marginbench.estimation.training import train_and_freeze

    cfg = load_config(config)
    res = train_and_freeze(cfg, EST, str(REPO_ROOT / "models" / "estimator_audit.json"), workers=workers)
    typer.echo(json.dumps(res, indent=1))


@app.command()
def prereg(config: str = typer.Option("configs/default.yaml", "--config"), workers: int = 4) -> None:
    """Calib power analysis, then write configs/plan.yaml and EXPERIMENT_PLAN.md."""
    from marginbench.experiments.prereg import build_plan, calib_analysis, write_plan
    from marginbench.hashing import to_jsonable, write_json

    calib = calib_analysis(EST, workers)
    write_json(REPO_ROOT / "results" / "calib" / "calib_analysis.json", calib)
    plan = to_jsonable(build_plan(calib, workers))
    h = write_plan(plan)
    typer.echo(json.dumps({"plan_hash": h, "n_eval": plan["power"]["n_eval"],
                           "materiality": plan["materiality"]["value_dollars"]}, indent=1))
    typer.echo("Now commit configs/plan.yaml and EXPERIMENT_PLAN.md with the message 'prereg: plan v1'.")


def _run_catalog(exp_id: str, output: str, plan: str, workers: int, guard: bool) -> None:
    from marginbench.experiments.execute import execute_experiment

    p, ph = _load_plan(plan, guard)
    spec = p["experiments"][exp_id]
    spec = {**spec, "contrasts": [tuple(c) for c in spec.get("contrasts", [])]}
    if "primary" in spec:
        spec["primary"] = tuple(spec["primary"])
    if "confirmatory" in spec:
        spec["confirmatory"] = [tuple(c) for c in spec["confirmatory"]]
    K = p["runtime_budget"]["K"]
    r = execute_experiment(exp_id, spec, EST, output, float(p["materiality"]["value_dollars"]), ph, workers=workers,
                           K=(K if K != load_config().planning.K else None),
                           label="OPEN_PREREGISTERED" if guard else "UNGUARDED")
    typer.echo(json.dumps(r, indent=1))
    raise typer.Exit(r["exit_code"])


@app.command()
def evaluate(plan: str = typer.Option(PLAN, "--plan"), output: str = typer.Option("results/primary", "--output"),
             workers: int = 4) -> None:
    """The preregistered PRIMARY evaluation (guarded)."""
    _run_catalog("PRIMARY", output, plan, workers, guard=True)


@app.command()
def experiment(id: str = typer.Option(..., "--id"), output: str = typer.Option(..., "--output"),
               plan: str = typer.Option(PLAN, "--plan"), workers: int = 4,
               no_guard: bool = typer.Option(False, "--no-guard", help="development only; labels the run UNGUARDED")) -> None:
    """Run a cataloged experiment (E0-E9, E-DEPLOY)."""
    if id == "E9":
        from marginbench.experiments.e9_gates import run_e9

        p, ph = _load_plan(plan, not no_guard)
        res = run_e9(EST, output, float(p["materiality"]["value_dollars"]), ph, int(p["E9"]["variant_seed"]),
                     n_truth=int(p["E9"]["n_truth"]), n_pilot=int(p["E9"]["n_pilot"]), workers=workers)
        typer.echo(json.dumps({"status": res["status"], "table": res["table"]}, indent=1))
        raise typer.Exit(EXIT[res["status"]])
    if id == "E8":
        from marginbench.experiments.e8 import run_e8

        p, ph = _load_plan(plan, not no_guard)
        res = run_e8(EST, output, float(p["materiality"]["value_dollars"]), ph, p["E8"]["cells"], n=int(p["E8"]["n"]),
                     workers=workers)
        typer.echo(json.dumps(res, indent=1))
        raise typer.Exit(EXIT[res["status"]])
    _run_catalog(id, output, plan, workers, guard=not no_guard)


@app.command()
def ablate(output: str = typer.Option("results/ablations", "--output"), plan: str = typer.Option(PLAN, "--plan"),
           workers: int = 4) -> None:
    """Required ablations against default (P0, P2, P4)."""
    _run_catalog("ABLATIONS", output, plan, workers, guard=True)


@app.command()
def sensitivity(output: str = typer.Option("results/sensitivity", "--output"), plan: str = typer.Option(PLAN, "--plan"),
                workers: int = 4, max_points: Optional[int] = None) -> None:
    """Latin-hypercube sensitivity design with M retrained per point."""
    from marginbench.experiments.sensitivity import run_sensitivity

    p, ph = _load_plan(plan, True)
    s = p["sensitivity"]
    pts = list(range(int(max_points))) if max_points else None
    res = run_sensitivity(output, ph, int(s["seed"]), n_points=int(s["n_points"]), reps_per_point=int(s["reps_per_point"]),
                          m_reps=int(s["materiality_reps_per_point"]), workers=workers, points=pts)
    typer.echo(json.dumps(res, indent=1))


@app.command()
def report(results: str = typer.Option(..., "--results"), output: Optional[str] = typer.Option(None, "--output")) -> None:
    """Rebuild report.html for a results directory (and the repo documents if --output is the repo root)."""
    from marginbench.reporting.html import build_report

    p = build_report(Path(results))
    typer.echo(str(p))
    if output:
        from marginbench.reporting.summary import write_documents

        write_documents(Path(output))


@app.command()
def reproduce(manifest: str = typer.Option(..., "--manifest"), workers: int = 4) -> None:
    """Re-run replication 0 for every arm and compare canonical hashes."""
    from marginbench.experiments.reproduce import reproduce_run

    res = reproduce_run(Path(manifest))
    typer.echo(json.dumps(res, indent=1))
    raise typer.Exit(0 if res["status"] == "REPRODUCED" else 3)


@app.command()
def audit(results: str = typer.Option(..., "--results")) -> None:
    """Audit every run directory under --results: reconciliation, traces, claims."""
    from marginbench.experiments.reproduce import audit_results

    res = audit_results(Path(results))
    typer.echo(json.dumps({k: v for k, v in res.items() if k != "runs"}, indent=1))
    raise typer.Exit(0 if res["status"] == "PASS" else 2)


if __name__ == "__main__":
    app()
