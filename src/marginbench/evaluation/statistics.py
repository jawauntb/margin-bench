"""Paired statistics (SPEC 14): t-intervals, TOST, bootstrap, Holm, materiality, power.

The replication is the unit of analysis. Requests within a replication are never treated
as independent.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Optional, Sequence

import numpy as np
from scipy import stats

T975_APPROX = 1.97
Z80 = 0.8416


@dataclass(frozen=True)
class PairedSummary:
    n: int
    mean: float
    sd: Optional[float]
    se: Optional[float]
    ci_low: Optional[float]
    ci_high: Optional[float]
    level: float
    p_value: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def paired_summary(diffs: Sequence[float], level: float = 0.95) -> PairedSummary:
    """Mean, sample SD, SE, two-sided Student-t interval at ``level``, and the two-sided
    paired t-test p-value of mean = 0."""
    x = np.asarray(list(diffs), dtype=float)
    n = int(x.size)
    if n == 0:
        return PairedSummary(0, float("nan"), None, None, None, None, level, None)
    mean = float(x.mean())
    if n < 2:
        return PairedSummary(n, mean, None, None, None, None, level, None)
    sd = float(x.std(ddof=1))
    se = sd / math.sqrt(n)
    tcrit = float(stats.t.ppf(0.5 + level / 2.0, df=n - 1))
    lo, hi = mean - tcrit * se, mean + tcrit * se
    if se == 0.0:
        p = 1.0 if mean == 0.0 else 0.0
    else:
        tstat = mean / se
        p = float(2.0 * stats.t.sf(abs(tstat), df=n - 1))
    return PairedSummary(n, mean, sd, se, lo, hi, level, p)


def tost(diffs: Sequence[float], margin: float, alpha: float = 0.05) -> dict[str, Any]:
    """Two one-sided t-tests for equivalence within (-margin, +margin)."""
    x = np.asarray(list(diffs), dtype=float)
    n = int(x.size)
    if n < 2 or margin <= 0:
        return {"passes": False, "p_lower": None, "p_upper": None, "alpha": alpha, "margin": margin}
    mean = float(x.mean())
    se = float(x.std(ddof=1)) / math.sqrt(n)
    if se == 0.0:
        ok = -margin < mean < margin
        return {"passes": bool(ok), "p_lower": 0.0 if mean > -margin else 1.0,
                "p_upper": 0.0 if mean < margin else 1.0, "alpha": alpha, "margin": margin}
    p_lower = float(stats.t.sf((mean + margin) / se, df=n - 1))  # H0: mu <= -m
    p_upper = float(stats.t.cdf((mean - margin) / se, df=n - 1))  # H0: mu >= +m
    return {"passes": bool(max(p_lower, p_upper) < alpha), "p_lower": p_lower, "p_upper": p_upper,
            "alpha": alpha, "margin": margin}


def bootstrap_ci(values: Sequence[float], seed: int, n_resamples: int = 10_000, level: float = 0.95,
                 stat: str = "mean") -> dict[str, Any]:
    x = np.asarray(list(values), dtype=float)
    if x.size == 0:
        return {"low": None, "high": None, "n_resamples": n_resamples, "seed": seed}
    g = np.random.Generator(np.random.PCG64DXSM(seed))
    idx = g.integers(0, x.size, size=(n_resamples, x.size))
    samples = x[idx]
    vals = samples.mean(axis=1) if stat == "mean" else np.quantile(samples, 0.05, axis=1)
    a = (1.0 - level) / 2.0
    return {"low": float(np.quantile(vals, a)), "high": float(np.quantile(vals, 1.0 - a)),
            "n_resamples": n_resamples, "seed": seed}


def cvar(values: Sequence[float], q: float = 0.05) -> Optional[float]:
    x = np.sort(np.asarray(list(values), dtype=float))
    if x.size == 0:
        return None
    k = max(1, int(math.floor(q * x.size)))
    return float(x[:k].mean())


def holm(pvalues: dict[str, float], family_alpha: float = 0.05) -> dict[str, dict[str, Any]]:
    """Holm step-down. The k-th smallest p-value (1-indexed) among N gets
    alpha_k = family_alpha / (N - k + 1). The sequence stops at the first non-rejection; that
    contrast and all later ones are marked ``stopped`` (SPEC 14.7)."""
    items = sorted(pvalues.items(), key=lambda kv: (kv[1], kv[0]))
    n = len(items)
    out: dict[str, dict[str, Any]] = {}
    stopped = False
    for k, (name, p) in enumerate(items, start=1):
        a = family_alpha / (n - k + 1)
        rejected = (not stopped) and (p <= a)
        if not rejected:
            stopped = True
        out[name] = {"rank": k, "alpha": a, "p_value": p, "rejected": rejected, "stopped": not rejected}
    return out


def materiality(mean_j_p0: float, floor: float = 1000.0, frac: float = 0.01) -> float:
    """m = max(0.01 * |mean J(P0)|, $1,000) (SPEC 14.3). Units: dollars."""
    return max(frac * abs(mean_j_p0), floor)


def required_n(sd: float, m: float) -> int:
    if m <= 0:
        raise ValueError("materiality must be positive")
    return int(math.ceil(((T975_APPROX + Z80) * sd / m) ** 2))


def n_eval_from(sd: float, m: float, floor: int = 200, cap: int = 2000) -> dict[str, Any]:
    nreq = required_n(sd, m)
    n_eval = min(max(floor, nreq), cap)
    return {"n_req": nreq, "n_eval": n_eval, "capped": nreq > cap}


def achieved_power(sd: float, m: float, n: int, effect: float) -> float:
    """P(classify an effect of size ``effect`` > 0 as directional) under a normal approximation:
    the CI must exclude 0 and the point estimate must pass m, i.e. mean > max(m, t*se)."""
    if n < 2 or sd <= 0:
        return 1.0 if effect >= m else 0.0
    se = sd / math.sqrt(n)
    tcrit = float(stats.t.ppf(0.975, df=n - 1))
    thresh = max(m, tcrit * se)
    return float(stats.norm.sf((thresh - effect) / se))
