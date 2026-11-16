"""Synthetic Yahoo chart responses for Track M tests (no network)."""

from __future__ import annotations

import datetime as dt
import math

from marginbench.markets.yahoo import ET


def sessions(start: dt.date, n: int) -> list[dt.date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def open_ts(day: dt.date) -> int:
    return int(dt.datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET).timestamp())


def chart(days: list[dt.date], closes: list[float], divs: dict[dt.date, float] | None = None) -> dict:
    ev = {str(open_ts(d)): {"amount": a, "date": open_ts(d)} for d, a in (divs or {}).items()}
    q = {"open": closes, "high": closes, "low": closes, "close": closes, "volume": [1] * len(closes)}
    return {"chart": {"result": [{"timestamp": [open_ts(d) for d in days], "indicators": {"quote": [q]},
                                  "events": {"dividends": ev}}]}}


def walk(n: int, sigma: float = 0.01, seed: int = 0, start: float = 100.0) -> list[float]:
    import numpy as np

    r = np.random.default_rng(seed).standard_normal(n) * sigma
    return [start * math.exp(x) for x in np.cumsum(r)]


def et(y: int, m: int, d: int, hh: int, mm: int) -> dt.datetime:
    return dt.datetime(y, m, d, hh, mm, tzinfo=ET).astimezone(dt.timezone.utc)
