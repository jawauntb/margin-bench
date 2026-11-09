"""Statistics and classification fixtures (SPEC 14, 18.5). Hand-computed values."""

import math

import pytest

from marginbench.evaluation.classification import PROXY_REVERSAL, VALUE, classify, evaluate_contrast
from marginbench.evaluation.statistics import (
    achieved_power,
    holm,
    materiality,
    n_eval_from,
    paired_summary,
    required_n,
    tost,
)
from marginbench.evaluation.toyworld import ToyWorld


def test_paired_mean_se_t_interval_hand_computed():
    s = paired_summary([1, 2, 3, 4, 5])
    assert s.n == 5 and s.mean == 3.0
    assert s.sd == pytest.approx(math.sqrt(2.5))
    assert s.se == pytest.approx(math.sqrt(2.5) / math.sqrt(5))
    t = 2.7764451051977987  # t_{0.975, 4}
    assert s.ci_low == pytest.approx(3 - t * math.sqrt(0.5))
    assert s.ci_high == pytest.approx(3 + t * math.sqrt(0.5))
    # p-value of t = 3 / sqrt(0.5) with 4 df
    # two-sided p for t = 3/sqrt(0.5), 4 df; closed form 1 - x(1 + (1 - x^2)/2), x = t/sqrt(t^2 + 4)
    x = (3 / math.sqrt(0.5)) / math.sqrt(18 + 4)
    assert s.p_value == pytest.approx(1 - x * (1 + 0.5 * (1 - x * x)), rel=1e-9)


def test_interval_level_and_degenerate_cases():
    s99 = paired_summary([1, 2, 3, 4, 5], level=0.99)
    assert s99.ci_high - s99.ci_low > paired_summary([1, 2, 3, 4, 5]).ci_high - paired_summary([1, 2, 3, 4, 5]).ci_low
    z = paired_summary([0.0] * 10)
    assert (z.mean, z.sd, z.ci_low, z.ci_high, z.p_value) == (0.0, 0.0, 0.0, 0.0, 1.0)
    one = paired_summary([3.0])
    assert one.ci_low is None and one.p_value is None


def test_tost_behavior():
    assert tost([0.1, -0.1, 0.05, -0.05, 0.0] * 4, margin=1.0)["passes"]
    assert not tost([0.1, -0.1, 0.05, -0.05, 0.0] * 4, margin=0.01)["passes"]
    assert not tost([5, 6, 7, 5, 6], margin=1.0)["passes"]
    assert not tost([1.0], margin=10)["passes"]
    assert tost([0.0] * 5, margin=1.0)["passes"]


def S(mean, lo, hi):
    from marginbench.evaluation.statistics import PairedSummary

    return PairedSummary(50, mean, 1.0, 0.1, lo, hi, 0.95, 0.01)


G_UP = S(0.1, 0.05, 0.15)
G_FLAT = S(0.0, -0.05, 0.05)
M = 100.0


@pytest.mark.parametrize("dj,dg,tost_pass,status,verified,expected", [
    (S(-500, -800, -200), G_UP, False, "INVALID", True, ("INVALID", False)),
    (S(-500, -800, -200), G_UP, False, "VALID", False, ("UNVERIFIED", False)),
    (S(-500, -800, -200), G_FLAT, False, "VALID", True, ("PROXY_NOT_IMPROVED", False)),
    (S(-500, -800, -200), G_UP, False, "VALID", True, ("REVERSAL_SUPPORTED", True)),
    (S(-150, -190, -50), G_UP, False, "VALID", True, ("REVERSAL_SUPPORTED", False)),
    (S(-50, -90, -10), G_UP, False, "VALID", True, ("INCONCLUSIVE", False)),
    (S(500, 200, 800), G_UP, False, "VALID", True, ("ALIGNMENT_SUPPORTED", False)),
    (S(1, -20, 20), G_UP, True, "VALID", True, ("EQUIVALENCE_SUPPORTED", False)),
    (S(1, -200, 200), G_UP, False, "VALID", True, ("INCONCLUSIVE", False)),
])
def test_proxy_reversal_branches(dj, dg, tost_pass, status, verified, expected):
    assert classify(PROXY_REVERSAL, dj, dg, M, tost_pass, status, verified) == expected


@pytest.mark.parametrize("dj,tost_pass,expected", [
    (S(500, 200, 800), False, "VALUE_HIGHER_SUPPORTED"),
    (S(-500, -800, -200), False, "VALUE_LOWER_SUPPORTED"),
    (S(1, -20, 20), True, "EQUIVALENCE_SUPPORTED"),
    (S(50, -20, 120), False, "INCONCLUSIVE"),
])
def test_value_branches_skip_proxy_precondition(dj, tost_pass, expected):
    assert classify(VALUE, dj, G_FLAT, M, tost_pass)[0] == expected
    assert classify(VALUE, dj, None, M, tost_pass)[0] == expected


def test_value_invalid_unverified():
    assert classify(VALUE, S(500, 200, 800), None, M, False, "INVALID")[0] == "INVALID"
    assert classify(VALUE, S(500, 200, 800), None, M, False, "UNVERIFIED")[0] == "UNVERIFIED"


def test_holm_stopped_contrast_cannot_be_directional():
    assert classify(VALUE, S(500, 200, 800), None, M, False, holm_stopped=True)[0] == "INCONCLUSIVE"
    assert classify(VALUE, S(1, -20, 20), None, M, True, holm_stopped=True)[0] == "EQUIVALENCE_SUPPORTED"
    assert classify(PROXY_REVERSAL, S(-500, -800, -200), G_UP, M, False, holm_stopped=True)[0] == "INCONCLUSIVE"


def test_holm_adjustment_and_stopping():
    res = holm({"a": 0.001, "b": 0.011, "c": 0.02, "d": 0.03, "e": 0.5})
    assert [res[k]["alpha"] for k in "abcde"] == pytest.approx([0.01, 0.0125, 0.05 / 3, 0.025, 0.05])
    assert [res[k]["rejected"] for k in "abcde"] == [True, True, False, False, False]
    assert [res[k]["stopped"] for k in "abcde"] == [False, False, True, True, True]
    # stopping: later p-values that would pass on their own are still stopped
    res2 = holm({"a": 0.02, "b": 0.021, "c": 0.022, "d": 0.023, "e": 0.024})
    assert not any(r["rejected"] for r in res2.values())


def test_identical_policies_give_zero_differences_exactly():
    from helpers import run_p0, small_cfg
    from marginbench.evaluation.metrics import compute_metrics

    cfg = small_cfg()
    _, a, _ = run_p0(cfg, rep=5)
    _, b, _ = run_p0(cfg, rep=5)
    ma = compute_metrics(a, cfg, cfg.time.horizon_days)
    mb = compute_metrics(b, cfg, cfg.time.horizon_days)
    assert ma["J_cents"] - mb["J_cents"] == 0
    r = evaluate_contrast("P0", "P0", PROXY_REVERSAL, [0.0] * 30, [0.0] * 30, 100.0)
    assert r.classification == "PROXY_NOT_IMPROVED"
    assert r.dJ["mean"] == 0.0


def test_materiality_and_power():
    assert materiality(250_000.0) == 2500.0
    assert materiality(-50_000.0) == 1000.0
    assert required_n(2000.0, 1000.0) == math.ceil(((1.97 + 0.8416) * 2.0) ** 2)
    assert n_eval_from(100.0, 1000.0) == {"n_req": 1, "n_eval": 200, "capped": False}
    big = n_eval_from(100_000.0, 1000.0)
    assert big["n_eval"] == 2000 and big["capped"]
    assert achieved_power(1000.0, 100.0, 400, 100.0) == pytest.approx(0.5, abs=0.02)
    assert achieved_power(1000.0, 100.0, 400, 200.0) > 0.95


def test_aligned_toy_world_exact():
    w = ToyWorld(pi=0.1, r=0.5, c_cb=20.0, L=50.0, v=18.0, d=12.0)
    sol = w.solve()
    assert sol["J"]["close"] == pytest.approx(-0.1 * 0.5 * 70.0)  # -3.5
    assert sol["J"]["verify"] == pytest.approx(-(18.0 + 1.2))  # -19.2
    assert sol["proxy_optimal"] == sol["value_optimal"] == "close"
    assert sol["regret_of_proxy_optimal"] == 0.0


def test_misaligned_toy_world_shows_exact_reversal():
    w = ToyWorld(pi=0.4, r=0.9, c_cb=20.0, L=400.0, v=18.0, d=12.0)
    sol = w.solve()
    assert sol["proxy_optimal"] == "close" and sol["value_optimal"] == "verify"
    assert sol["J"]["close"] == pytest.approx(-0.4 * 0.9 * 420.0)  # -151.2
    assert sol["J"]["verify"] == pytest.approx(-22.8)
    dG = sol["G"]["close"] - sol["G"]["verify"]
    dJ = sol["J"]["close"] - sol["J"]["verify"]
    assert dG > 0 and dJ < 0  # a proxy reversal by the SPEC 2.3 definition
    assert sol["regret_of_proxy_optimal"] == pytest.approx(151.2 - 22.8)
