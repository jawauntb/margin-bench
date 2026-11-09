"""Discounting and the business-value objective J (SPEC 2.2, 6.3)."""

from __future__ import annotations


def discounted_contribution_cents(daily_operator_cents: list[int], d0: int, d_end: int, delta: float) -> int:
    """J in cents: sum over days d0..d_end (inclusive) of delta**(d-d0) * c_d.

    Each day-total is discounted once in floating point; only the window total is rounded
    to cents. Individual discounted entries are never rounded (SPEC 6.3).
    """
    total = 0.0
    for d in range(d0, d_end + 1):
        c = daily_operator_cents[d]
        if c:
            total += (delta ** (d - d0)) * c
    return int(round(total))


def cumulative_discounted(daily_operator_cents: list[int], d0: int, d_end: int, delta: float) -> list[float]:
    out = []
    acc = 0.0
    for d in range(d0, d_end + 1):
        acc += (delta ** (d - d0)) * daily_operator_cents[d]
        out.append(acc)
    return out
