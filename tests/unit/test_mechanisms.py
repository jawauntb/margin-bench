import math

import pytest

from marginbench.config import load_config
from marginbench.economics.contracts import annual_fee_cents, cumulative_fee_cents, daily_fee_cents
from marginbench.economics.valuation import discounted_contribution_cents
from marginbench.environment.callbacks import benign_repeat_delay, callback_delay_minutes, callback_probability
from marginbench.environment.losses import loss_amount_cents, split_loss
from marginbench.environment.repairs import contractor_report, repair_outcome, success_probability
from marginbench.environment.retention import features, hazard, trailing_sum
from marginbench.environment.sla import sla_credit_cents, sla_deadline
from marginbench.environment.verification import verification_result

CFG = load_config()


def sig(x):
    return 1 / (1 + math.exp(-x))


def test_repair_probability_formula():
    lg = math.log(0.82 / 0.18)
    p = success_probability(CFG, lg, 0.1, "urgent", 0.9, 2)
    assert p == pytest.approx(sig(lg + 0.1 - 0.5 + 1.0 * (0.9 - 0.7) - 0.4 * 2))
    assert success_probability(CFG, lg, 0.0, "minor", 0.7, 0) == pytest.approx(sig(lg + 0.5))


def test_repair_outcome_and_already_resolved():
    assert repair_outcome(True, 0.0, 0.99) is True
    assert repair_outcome(False, 0.6, 0.59) is True
    assert repair_outcome(False, 0.6, 0.61) is False


def test_contractor_report_rates():
    assert contractor_report(CFG, True, 0.979) == "complete"
    assert contractor_report(CFG, True, 0.981) == "needs_return"
    assert contractor_report(CFG, False, 0.79) == "complete"
    assert contractor_report(CFG, False, 0.81) == "needs_return"


def test_verification_sensitivity_specificity():
    assert verification_result(CFG, False, 0.89) == "fail"
    assert verification_result(CFG, False, 0.91) == "ok"
    assert verification_result(CFG, True, 0.94) == "ok"
    assert verification_result(CFG, True, 0.96) == "fail"
    perfect = load_config(overlays=[{"verify": {"perfect": True}}])
    assert verification_result(perfect, False, 0.999) == "fail"
    assert verification_result(perfect, True, 0.999) == "ok"


def test_callback_probability_and_suppression():
    assert callback_probability(CFG, 0.8, "moderate", True) == pytest.approx(0.8 * 0.80 * 0.85)
    assert callback_probability(CFG, 0.8, "moderate", False) == pytest.approx(0.8 * 0.80)
    ns = load_config(overlays=[{"callbacks": {"no_suppression": True}}])
    assert callback_probability(ns, 0.8, "urgent", True) == pytest.approx(0.8 * 0.97)
    off = load_config(overlays=[{"callbacks": {"off": True}}])
    assert callback_probability(off, 0.8, "urgent", True) == 0.0
    assert benign_repeat_delay(off, 0.0, 0.5) is None
    assert callback_delay_minutes(CFG, 2.0) == int(round(2.0 * 4.0 * 1440))


def test_benign_repeat():
    assert benign_repeat_delay(CFG, 0.029, 0.5) == int(0.5 * 30 * 1440)
    assert benign_repeat_delay(CFG, 0.031, 0.5) is None


def test_sla_deadline_and_credit():
    assert sla_deadline(CFG, 100, "urgent") == 100 + 24 * 60
    assert sla_deadline(CFG, 0, "minor") == 7 * 1440
    assert sla_credit_cents(CFG, "urgent") == 4000
    assert sla_credit_cents(CFG, "moderate") == 1500
    assert sla_credit_cents(CFG, "minor") == 0


def test_loss_payer_rule():
    assert split_loss(CFG, 100000, False) == (0, 100000)
    assert split_loss(CFG, 100000, True) == (25000, 75000)
    half = load_config(overlays=[{"loss": {"operator_negligence_share": 0.5}}])
    assert split_loss(half, 100001, True) == (50000, 50001)
    assert loss_amount_cents(CFG, "urgent", 0.0) == 600000


def test_retention_hazard():
    h0 = -math.log(1 - 0.06) / 365
    assert CFG.retention.h0 == pytest.approx(h0)
    f = {"cb": 0.2, "br": 1.0, "sl": 0.0, "oc": 0.5}
    assert hazard(CFG, f) == pytest.approx(h0 * math.exp(2.0 * 0.2 + 0.10 * 1.0 + 0.15 * 0.5))
    null = load_config(overlays=[{"retention": {"null_scenario": True}}])
    assert hazard(null, f) == pytest.approx(h0)


def test_trailing_window_features():
    log = [(5, 1.0), (94, 1.0), (95, 1.0), (100, 1.0)]
    assert trailing_sum(log, 100, 90) == 2.0  # days 10..99 -> 94, 95
    feats = features([(99, 1.0)], [(50, 1.0)], [(0, 1.0)], [(99, 500.0)], 10, 100)
    assert feats == {"cb": 0.1, "br": 1.0, "sl": 1.0, "oc": 0.5}


def test_fee_accrual_sums_exactly_over_365_days():
    annual = annual_fee_cents(120.0, 10)
    assert annual == 1_440_000
    assert sum(daily_fee_cents(annual, d) for d in range(365)) == annual
    assert cumulative_fee_cents(annual, 365) == annual
    assert all(daily_fee_cents(annual, d) in (3945, 3946) for d in range(365))
    odd = annual_fee_cents(99.99, 7)
    assert sum(daily_fee_cents(odd, d) for d in range(365)) == odd


def test_discounting():
    delta = 1.10 ** (-1 / 365)
    assert CFG.time.delta == pytest.approx(delta)
    daily = [0] * 5 + [100, 100, 100]
    assert discounted_contribution_cents(daily, 5, 7, delta) == round(100 + 100 * delta + 100 * delta**2)
    assert discounted_contribution_cents(daily, 5, 7, 1.0) == 300
