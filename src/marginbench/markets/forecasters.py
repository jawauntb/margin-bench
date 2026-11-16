"""Baseline forecasters for task ``ret1d``: pure functions of past data only.

Each returns the daily standard deviation sigma of the next session's total log return, or None
when it cannot speak (too little history, a failed fit, no implied input for that session). The
predictive distribution is Normal(0, sigma) read at the task's quantile levels. Normal tails are
a declared simplification (DECISIONS D-51): the coverage columns of the leaderboard show where
it fails, which is part of what the track measures.

- ``rw20``: sample sd of the last ``window`` returns (the reference).
- ``ewma``: RiskMetrics exponentially weighted variance with decay ``lambda``.
- ``garch11``: GARCH(1,1) fitted by Gaussian maximum likelihood on the last ``window`` returns.
- ``implied``: an implied-vol index close at the base session (``^VIX`` for SPY), annualized
  over 252 sessions. It is the market's own forecast, risk-neutral and 30-day, so it carries
  the variance risk premium: beating it is the test that matters.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.stats import norm

Sigma = Callable[[np.ndarray, dict[str, Any], dict[str, Any]], "float | None"]


def total_log_returns(close: list[float], sessions: list[str], div: dict[str, float]) -> np.ndarray:
    """r[i] = ln((C[i+1] + D[i+1]) / C[i]), with D the dividend going ex on session i+1."""
    c = np.asarray(close, dtype=float)
    d = np.array([div.get(s, 0.0) for s in sessions[1:]], dtype=float)
    return np.log((c[1:] + d) / c[:-1])


def rw(r: np.ndarray, p: dict[str, Any], _: dict[str, Any]) -> float | None:
    w = int(p["window"])
    if len(r) < w:
        return None
    return float(np.std(r[-w:], ddof=1))


def ewma(r: np.ndarray, p: dict[str, Any], _: dict[str, Any]) -> float | None:
    lam, warm = float(p["lambda"]), int(p["warmup"])
    if len(r) < warm:
        return None
    var = float(np.var(r[:20], ddof=1))
    for x in r[20:]:
        var = lam * var + (1.0 - lam) * float(x) ** 2
    return math.sqrt(var)


def _garch_path(theta: np.ndarray, x: np.ndarray, v0: float) -> np.ndarray:
    """Conditional variances v[0..n]: v[0] = v0, v[t] = om + a x[t-1]^2 + b v[t-1]; v[n] is next."""
    om, a, b = theta
    y, _ = lfilter([1.0], [1.0, -b], om + a * x * x, zi=[b * v0])
    return np.concatenate(([v0], y))


def _garch_nll(theta: np.ndarray, x: np.ndarray, v0: float) -> float:
    om, a, b = theta
    if om <= 0 or a < 0 or b < 0 or a + b >= 0.9999:
        return 1e10
    v = _garch_path(theta, x, v0)[:-1]
    return float(0.5 * np.sum(np.log(v) + x * x / v))


def garch11(r: np.ndarray, p: dict[str, Any], _: dict[str, Any]) -> float | None:
    w = int(p["window"])
    if len(r) < w:
        return None
    x = np.asarray(r[-w:], dtype=float)
    v0 = float(np.var(x, ddof=1))
    res = minimize(
        _garch_nll, np.array([v0 * 0.05, 0.08, 0.90]), args=(x, v0), method="Nelder-Mead",
        options={"xatol": 1e-10, "fatol": 1e-10, "maxiter": 4000},
    )
    th = np.asarray(res.x, dtype=float)
    om, a, b = (float(t) for t in th)
    if not res.success or om <= 0 or a < 0 or b < 0 or a + b >= 0.9999:
        return None
    return math.sqrt(float(_garch_path(th, x, v0)[-1]))


def implied(_: np.ndarray, p: dict[str, Any], aux: dict[str, Any]) -> float | None:
    """aux['implied'] is the index close at the base session, or None when it is missing."""
    level = aux.get("implied")
    if level is None or level <= 0:
        return None
    return float(level) / 100.0 / math.sqrt(252.0)


KINDS: dict[str, Sigma] = {"rw": rw, "ewma": ewma, "garch11": garch11, "implied": implied}


def quantiles(sigma: float, levels: list[float]) -> list[float]:
    return [float(sigma * norm.ppf(a)) for a in levels]
