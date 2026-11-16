"""Append-only JSON-lines files for Track M. First write wins; nothing is edited or deleted.

Layout under one ledger directory (the ``markets-ledger`` branch on the nightly):
  forecasts.jsonl     public forecasts (tape.forecast)
  commitments.jsonl   hashes of private forecasts, recorded before their outcome (tape.commitment)
  outcomes.jsonl      realized outcomes, one per (task, symbol, base_session)
  scores.jsonl        one row per settled (forecast, outcome) pair, public or private
  leaderboard.json    rebuilt from scores.jsonl every night (derived, overwritten)
  LEADERBOARD.md      the same, for people
  receipts/<date>.json  what one nightly read, wrote and hashed
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

from marginbench.hashing import canonical_json

FILES = ("forecasts", "commitments", "outcomes", "scores")


def path(root: str | Path, name: str) -> Path:
    return Path(root) / f"{name}.jsonl"


def read(root: str | Path, name: str) -> list[dict[str, Any]]:
    p = path(root, name)
    if not p.exists():
        return []
    rows = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:  # a torn line is a hold, never skipped silently
                raise ValueError(f"{p}:{n}: not JSON ({e})") from e
    return rows


def append(
    root: str | Path, name: str, rows: Iterable[dict[str, Any]], key: Callable[[dict[str, Any]], Any]
) -> int:
    """Append rows whose key is not already present. Returns how many were written."""
    have = {key(r) for r in read(root, name)}
    p = path(root, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(p, "a", encoding="utf-8") as fh:
        for r in rows:
            k = key(r)
            if k in have:
                continue
            have.add(k)
            fh.write(canonical_json(r) + "\n")
            n += 1
    return n
