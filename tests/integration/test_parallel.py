"""Parallel execution is byte-identical to serial on 4 replications (SPEC 17.2)."""

from marginbench.config import REPO_ROOT
from marginbench.experiments.runner import make_jobs, run_jobs
from marginbench.hashing import canonical_json
from helpers import small_cfg


def strip(res):
    out = []
    for r in res:
        arms = {p: {k: v for k, v in a.items() if k not in ("wall_seconds", "diagnostics")} for p, a in r["arms"].items()}
        out.append({**r, "arms": arms})
    return out


def test_parallel_equals_serial():
    cfg = small_cfg()
    est = str(REPO_ROOT / "models" / "estimator_v1.json")
    jobs = make_jobs("T", "w", cfg, est, "dev", [0, 1, 2, 3], [{"name": "P0"}, {"name": "P2"}], None, K=8)
    a, sa = run_jobs(jobs, None, workers=1)
    b, sb = run_jobs(jobs, None, workers=4)
    assert sa == sb == "VALID"
    assert canonical_json(strip(a)) == canonical_json(strip(b))
