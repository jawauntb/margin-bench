"""Settlement: the realized outcome of task ``ret1d`` and the validity of each forecast.

The target of a forecast with base session B is the first final session after B in the public
bars, whatever the calendar says (no holiday table to keep). Its outcome is the total log return
ln((C_T + D_T) / C_B). A forecast is valid only if it was issued before the target session
opened; for a private forecast, its commitment must also have been recorded before that open.
An invalid forecast is scored as invalid and never enters a comparison.
"""

from __future__ import annotations

import math
from typing import Any

from marginbench.hashing import canonical_hash
from marginbench.markets import tape


def outcome(task: str, symbol: str, base_session: str, ser: dict[str, Any]) -> dict[str, Any] | None:
    s = ser["sessions"]
    if base_session not in s:
        return None
    i = s.index(base_session)
    if i + 1 >= len(s):
        return None  # target not final yet
    j = i + 1
    target = s[j]
    y = math.log((ser["close"][j] + ser["div"].get(target, 0.0)) / ser["close"][i])
    row = {
        "v": tape.VERSION, "task": task, "symbol": symbol, "base_session": base_session,
        "target_session": target, "target_open_at": ser["open_at"][j], "y": y,
        "inputs": [ser["ids"][i], ser["ids"][j]],
    }
    row["id"] = canonical_hash(row)
    return row


def validity(fc: dict[str, Any], out: dict[str, Any], commit: dict[str, Any] | None) -> str | None:
    """None when valid, else the reason it is not."""
    opened = tape.parse_iso(out["target_open_at"])
    if tape.parse_iso(fc["issued_at"]) >= opened:
        return "issued after the target session opened"
    if fc["visibility"] == "private":
        if commit is None:
            return "private forecast with no public commitment"
        if tape.parse_iso(commit["recorded_at"]) >= opened:
            return "commitment recorded after the target session opened"
    return None
