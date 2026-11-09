"""Owner retention hazard (SPEC 5.11)."""

from __future__ import annotations

import math

from marginbench.config import Config

WINDOWS = {"cb": 90, "br": 90, "sl": 365, "oc": 90}


def trailing_sum(log: list[tuple[int, float]], day: int, window: int) -> float:
    """Sum of weights for events on days [day - window, day - 1]."""
    lo = day - window
    return float(sum(w for d, w in log if lo <= d < day))


def features(callback_log, breach_log, loss_log, spend_log, units: int, day: int) -> dict[str, float]:
    return {
        "cb": trailing_sum(callback_log, day, WINDOWS["cb"]) / units,
        "br": trailing_sum(breach_log, day, WINDOWS["br"]),
        "sl": trailing_sum(loss_log, day, WINDOWS["sl"]),
        "oc": trailing_sum(spend_log, day, WINDOWS["oc"]) / units / 100.0,
    }


def hazard(cfg: Config, feats: dict[str, float]) -> float:
    b = cfg.retention.betas()
    lin = sum(b[k] * feats[k] for k in ("cb", "br", "sl", "oc"))
    return cfg.retention.h0 * math.exp(min(lin, 50.0))
