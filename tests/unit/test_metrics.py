from types import SimpleNamespace

from marginbench.config import load_config
from marginbench.economics.ledger import Ledger
from marginbench.evaluation.metrics import compute_metrics, proxy_value
from marginbench.evaluation.validation import validate_transitions
from helpers import run_p0, small_cfg

CFG = load_config()


def test_proxy_formula_and_undefined():
    assert proxy_value(0.8, 500.0, 10, CFG) == 0.8 - 0.5 * (500.0 / 10) / 25
    assert proxy_value(None, 0.0, 0, CFG) is None
    assert proxy_value(0.5, 0.0, 0, CFG) is None


def empty_out():
    return SimpleNamespace(requests={}, ledger=Ledger("x"), callback_ticks={}, events=[], action_records=[],
                           contractors={}, contracts={}, boundary={"unreported_failures": 0})


def test_empty_cohort_metrics_are_null_with_reason():
    m = compute_metrics(empty_out(), CFG, CFG.time.horizon_days)
    assert m["N"] == 0
    for k in ("G", "closure_rate", "opex_per_request", "verified_resolution_rate", "true_resolution_rate",
              "reopen_rate", "callback_rate_per_completed_attempt", "escalation_rate", "verification_rate",
              "backlog_age_days", "time_to_first_closure_days_mean"):
        assert m[k] is None, k
    assert m["undefined"]["G"] == "empty cohort (N = 0)"
    assert m["J_cents"] == 0


def test_real_run_metric_ranges():
    cfg = small_cfg()
    _, out, _ = run_p0(cfg)
    m = compute_metrics(out, cfg, cfg.time.horizon_days)
    assert m["N"] > 0
    for k in ("closure_rate", "verified_resolution_rate", "true_resolution_rate", "reopen_rate"):
        assert 0.0 <= m[k] <= 1.0
    assert m["opex_dollars"] >= 0
    assert m["G"] == proxy_value(m["closure_rate"], m["opex_dollars"], m["N"], cfg)
    assert validate_transitions(out.events) == []
