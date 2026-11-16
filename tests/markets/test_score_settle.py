import math

import numpy as np
import pytest

from marginbench.markets import forecasters as F
from marginbench.markets import score, settle, tape

LV = [0.05, 0.25, 0.5, 0.75, 0.95]


def test_pinball_known_values():
    assert score.pinball(0.9, 1.0, 0.0) == pytest.approx(0.1)   # over-forecast at a high level: cheap
    assert score.pinball(0.9, 0.0, 1.0) == pytest.approx(0.9)   # under-forecast at a high level: dear
    assert score.pinball(0.5, 0.0, 0.0) == 0.0


def test_quantile_score_prefers_the_true_distribution():
    rng = np.random.default_rng(3)
    y = rng.standard_normal(4000) * 0.01
    good = [score.quantile_score(LV, F.quantiles(0.01, LV), v) for v in y]
    wide = [score.quantile_score(LV, F.quantiles(0.03, LV), v) for v in y]
    narrow = [score.quantile_score(LV, F.quantiles(0.003, LV), v) for v in y]
    assert np.mean(good) < np.mean(wide) and np.mean(good) < np.mean(narrow)


def test_hits_per_central_interval():
    h = score.hits(LV, [-2, -1, 0, 1, 2], 1.5)
    assert h == {"0.90": 1, "0.50": 0}


def _ser():
    return {"sessions": ["2026-11-12", "2026-11-13", "2026-11-16"], "close": [100.0, 100.0, 101.0],
            "open_at": ["2026-11-12T14:30:00Z", "2026-11-13T14:30:00Z", "2026-11-16T14:30:00Z"],
            "ids": ["a", "b", "c"], "div": {"2026-11-16": 0.5}}


def test_outcome_is_next_final_session_with_dividend():
    out = settle.outcome("ret1d", "SPY", "2026-11-13", _ser())
    assert out["target_session"] == "2026-11-16"
    assert out["y"] == pytest.approx(math.log(101.5 / 100.0))
    assert settle.outcome("ret1d", "SPY", "2026-11-16", _ser()) is None  # target not final
    assert settle.outcome("ret1d", "SPY", "2026-11-11", _ser()) is None  # unknown base


def _fc(issued, vis="public"):
    return tape.forecast(task="ret1d", forecaster="f", symbol="SPY", issued_at=issued, base_session="2026-11-13",
                         levels=LV, quantiles=F.quantiles(0.01, LV), inputs_sha256="x", visibility=vis)


def test_validity_requires_issue_and_commitment_before_the_open():
    out = settle.outcome("ret1d", "SPY", "2026-11-13", _ser())
    assert settle.validity(_fc("2026-11-14T01:00:00Z"), out, None) is None
    assert "after the target session opened" in settle.validity(_fc("2026-11-16T15:00:00Z"), out, None)
    p = _fc("2026-11-14T01:00:00Z", "private")
    assert "no public commitment" in settle.validity(p, out, None)
    assert "after the target" in settle.validity(p, out, tape.commitment(p, "2026-11-16T14:31:00Z"))
    assert settle.validity(p, out, tape.commitment(p, "2026-11-14T01:01:00Z")) is None


def _rows(diff, n, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        base = abs(rng.standard_normal()) + 1.0
        for f, q in (("inc", base), ("ch", base - diff + rng.standard_normal() * 0.1)):
            rows.append({"valid": True, "forecaster": f, "symbol": "SPY", "target_session": f"s{i:04d}",
                         "qs": q, "task": "ret1d", "hits": {}, "visibility": "public"})
    return rows


CFG = {"min_n": 30, "ci": 0.9, "block": 5, "draws": 1000}


def test_gate_states():
    assert score.compare(_rows(0.2, 50), "inc", "ch", "ret1d", None)["state"] == "off"
    c = score.compare(_rows(0.2, 10), "inc", "ch", "ret1d", CFG)
    assert c["state"] == "collecting" and c["text"] == "n 10 < 30"
    assert score.compare(_rows(0.2, 200), "inc", "ch", "ret1d", CFG)["state"] == "pass"
    assert score.compare(_rows(0.0, 200), "inc", "ch", "ret1d", CFG)["state"] == "fail"
    assert score.compare(_rows(-0.2, 200), "inc", "ch", "ret1d", CFG)["state"] == "fail"
    assert score.compare(_rows(0.2, 50), "inc", "ch", "ret1d", {**CFG, "min_n": None})["state"] == "collecting"


def test_gate_is_deterministic():
    a = score.compare(_rows(0.05, 120), "inc", "ch", "ret1d", CFG)
    b = score.compare(_rows(0.05, 120), "inc", "ch", "ret1d", CFG)
    assert a == b


def test_invalid_rows_never_enter_a_comparison():
    rows = _rows(0.2, 60)
    for r in rows:
        if r["forecaster"] == "ch":
            r["valid"] = False
    assert score.compare(rows, "inc", "ch", "ret1d", CFG)["n"] == 0


def test_forecasters_point_in_time_and_none_when_short():
    r = np.random.default_rng(1).standard_normal(800) * 0.01
    assert F.rw(r, {"window": 20}, {}) == pytest.approx(np.std(r[-20:], ddof=1))
    assert F.rw(r[:5], {"window": 20}, {}) is None
    assert F.garch11(r[:100], {"window": 750}, {}) is None
    assert F.implied(r, {}, {"implied": 15.87}) == pytest.approx(0.1587 / math.sqrt(252))
    assert F.implied(r, {}, {}) is None
    g = F.garch11(r, {"window": 750}, {})
    assert 0.008 < g < 0.012
