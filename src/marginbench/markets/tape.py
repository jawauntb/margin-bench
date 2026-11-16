"""The two envelopes every producer and consumer agrees on (docs/TRACK-M.md section 2).

An Observation is one fact as it was true at ``observed_at``. A Forecast is one predictive
distribution issued at ``issued_at`` for an outcome that did not exist yet. Both are content
addressed: ``id`` is the SHA-256 of the canonical JSON of every field except ``id`` and
``recorded_at``, so the same fact recorded twice has the same id and is stored once.

hvega writes Observations with its own stdlib copy of this rule (``hvega.tape``); the shared
fixture ``tests/markets/fixtures/envelope_v1.json`` pins both to the same ids.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from marginbench.hashing import canonical_hash

VERSION = 1
VISIBILITY = ("public", "private")
_OBS_FIELDS = ("v", "kind", "source", "producer", "symbol", "observed_at", "visibility", "payload")
_FC_FIELDS = (
    "v", "task", "forecaster", "symbol", "issued_at", "base_session", "levels", "quantiles",
    "inputs_sha256", "visibility",
)
_UNHASHED = ("id", "recorded_at")


class EnvelopeError(ValueError):
    """A row that is not a valid v1 envelope. Callers treat it as a hold, never as data."""


def utc_iso(t: dt.datetime) -> str:
    """ISO-8601 in UTC with a trailing Z and whole seconds."""
    if t.tzinfo is None:
        raise EnvelopeError("naive datetime: every time in an envelope is timezone-aware")
    return t.astimezone(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> dt.datetime:
    if not isinstance(s, str) or not s.endswith("Z"):
        raise EnvelopeError(f"time must be UTC ISO-8601 ending in Z: {s!r}")
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def content_id(row: dict[str, Any]) -> str:
    return canonical_hash({k: v for k, v in row.items() if k not in _UNHASHED})


def _check(row: dict[str, Any], fields: tuple[str, ...], what: str) -> None:
    missing = [f for f in fields if f not in row]
    if missing:
        raise EnvelopeError(f"{what} missing {missing}")
    extra = sorted(set(row) - set(fields) - set(_UNHASHED))
    if extra:
        raise EnvelopeError(f"{what} has unknown fields {extra}")
    if row["v"] != VERSION:
        raise EnvelopeError(f"{what} version {row['v']!r} is not {VERSION}")
    if row["visibility"] not in VISIBILITY:
        raise EnvelopeError(f"{what} visibility {row['visibility']!r}")
    if "id" in row and row["id"] != content_id(row):
        raise EnvelopeError(f"{what} id does not match its content")


def observation(
    *, kind: str, source: str, producer: str, symbol: str | None, observed_at: str,
    payload: dict[str, Any], visibility: str = "public", recorded_at: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "v": VERSION, "kind": kind, "source": source, "producer": producer, "symbol": symbol,
        "observed_at": observed_at, "visibility": visibility, "payload": payload,
    }
    parse_iso(observed_at)
    row["id"] = content_id(row)
    if recorded_at is not None:
        row["recorded_at"] = recorded_at
    validate_observation(row)
    return row


def validate_observation(row: dict[str, Any]) -> dict[str, Any]:
    _check(row, _OBS_FIELDS, "observation")
    parse_iso(row["observed_at"])
    return row


def forecast(
    *, task: str, forecaster: str, symbol: str, issued_at: str, base_session: str,
    levels: list[float], quantiles: list[float], inputs_sha256: str, visibility: str = "public",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "v": VERSION, "task": task, "forecaster": forecaster, "symbol": symbol,
        "issued_at": issued_at, "base_session": base_session, "levels": list(levels),
        "quantiles": list(quantiles), "inputs_sha256": inputs_sha256, "visibility": visibility,
    }
    row["id"] = content_id(row)
    validate_forecast(row)
    return row


def validate_forecast(row: dict[str, Any]) -> dict[str, Any]:
    _check(row, _FC_FIELDS, "forecast")
    parse_iso(row["issued_at"])
    lv, q = row["levels"], row["quantiles"]
    if len(lv) != len(q) or not lv:
        raise EnvelopeError("forecast levels and quantiles must be non-empty and the same length")
    if any(not 0.0 < a < 1.0 for a in lv) or any(b <= a for a, b in zip(lv, lv[1:])):
        raise EnvelopeError("forecast levels must be strictly increasing inside (0, 1)")
    if any(b < a for a, b in zip(q, q[1:])):
        raise EnvelopeError("forecast quantiles must be non-decreasing (no crossing)")
    return row


def commitment(fc: dict[str, Any], recorded_at: str) -> dict[str, Any]:
    """The public trace of a private forecast: who, what, when, and the hash. Nothing else."""
    return {
        "v": VERSION, "kind": "commitment", "forecast_id": fc["id"], "task": fc["task"],
        "forecaster": fc["forecaster"], "symbol": fc["symbol"], "base_session": fc["base_session"],
        "issued_at": fc["issued_at"], "recorded_at": recorded_at,
    }
