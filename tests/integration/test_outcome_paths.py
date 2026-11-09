"""Every outcome path is producible from synthetic paired results (SPEC 18.6)."""

import numpy as np
import pytest

from marginbench.experiments.pairing import analyze_contrasts

M = 1000.0


def fake_results(dj, dg, status="VALID"):
    out = []
    for i, (j, g) in enumerate(zip(dj, dg)):
        out.append({"world": "w", "replication": i, "arms": {
            "P0": {"J": 100_000.0, "G": 0.5, "status": "VALID", "event_hash": "x"},
            "P2": {"J": 100_000.0 + j, "G": 0.5 + g, "status": status, "event_hash": "y"},
            "P4": {"J": 100_000.0 + j, "G": 0.5 + g, "status": status, "event_hash": "z"}}})
    return out


def noisy(mean, sd, n=200, seed=0):
    g = np.random.Generator(np.random.PCG64DXSM(seed))
    return list(mean + sd * g.standard_normal(n))


@pytest.mark.parametrize("pair,dj,dg,status,verified,expected", [
    (("P2", "P0"), noisy(-5000, 1000), noisy(0.1, 0.01), "VALID", True, "REVERSAL_SUPPORTED"),
    (("P2", "P0"), noisy(5000, 1000), noisy(0.1, 0.01), "VALID", True, "ALIGNMENT_SUPPORTED"),
    (("P4", "P0"), noisy(5000, 1000), noisy(0.0, 0.01), "VALID", True, "VALUE_HIGHER_SUPPORTED"),
    (("P4", "P0"), noisy(-5000, 1000), noisy(0.0, 0.01), "VALID", True, "VALUE_LOWER_SUPPORTED"),
    (("P4", "P0"), noisy(0, 100), noisy(0.0, 0.01), "VALID", True, "EQUIVALENCE_SUPPORTED"),
    (("P4", "P0"), noisy(500, 5000, n=20), noisy(0.0, 0.01, n=20), "VALID", True, "INCONCLUSIVE"),
    (("P2", "P0"), noisy(-5000, 1000), noisy(-0.1, 0.01), "VALID", True, "PROXY_NOT_IMPROVED"),
    (("P2", "P0"), noisy(-5000, 1000), noisy(0.1, 0.01), "INVALID", True, "INVALID"),
    (("P2", "P0"), noisy(-5000, 1000), noisy(0.1, 0.01), "VALID", False, "UNVERIFIED"),
])
def test_outcome_paths(pair, dj, dg, status, verified, expected):
    res = fake_results(dj, dg, status)
    an = analyze_contrasts(res, "w", [pair], M, "TEST", verified=verified)
    assert an["contrasts"][f"{pair[0]}-{pair[1]}"]["classification"] == expected


def test_holm_family_through_pipeline():
    res = fake_results(noisy(-5000, 1000), noisy(0.1, 0.01))
    an = analyze_contrasts(res, "w", [("P2", "P0"), ("P4", "P0")], M, "TEST", primary=("P2", "P0"),
                           confirmatory=[("P4", "P0")])
    assert an["contrasts"]["P2-P0"]["label"] == "PRIMARY"
    assert an["contrasts"]["P4-P0"]["label"] == "CONFIRMATORY"
    assert an["contrasts"]["P4-P0"]["holm"]["alpha"] == 0.05
