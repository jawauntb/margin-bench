"""Policy integration: every feasible policy runs, reconciles, and matched pairs share samples."""

from marginbench.config import REPO_ROOT, public_config
from marginbench.estimation.estimator import FrozenEstimator
from marginbench.experiments.runner import make_jobs, replication_job
from marginbench.policies.internal_model import uniform_matrix
from helpers import small_cfg


def test_all_policies_valid_and_reconciled():
    cfg = small_cfg()
    est = str(REPO_ROOT / "models" / "estimator_v1.json")
    job = make_jobs("T", "w", cfg, est, "dev", [0], [{"name": p} for p in ("P0", "P1", "P2", "P3", "P4", "P5")], None, K=4)[0]
    r = replication_job(job)
    for p, a in r["arms"].items():
        assert a["status"] == "VALID", (p, a["reconciliation_errors"], a["transition_errors"])


def test_common_random_numbers_shared():
    assert (uniform_matrix(123, 8) == uniform_matrix(123, 8)).all()
    assert not (uniform_matrix(123, 8) == uniform_matrix(124, 8)).all()


def test_internal_model_does_not_import_environment():
    import marginbench.policies.internal_model as im

    src = open(im.__file__).read()
    assert "marginbench.environment" not in src
