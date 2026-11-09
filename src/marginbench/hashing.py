"""Canonical JSON and hashing (SPEC 17.4).

Canonical JSON: sorted keys, no whitespace, floats via ``repr`` (shortest round trip),
timestamps as integer ticks. NaN and infinities are rejected: undefined values must be
serialized as ``null`` with a reason (SPEC 16).
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def to_jsonable(obj: Any) -> Any:
    """Convert dataclasses, enums, numpy scalars, tuples and pydantic models to JSON types."""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        if math.isnan(f) or math.isinf(f):
            raise ValueError("non-finite float in canonical JSON; use null with a reason")
        return f
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [to_jsonable(v) for v in obj.tolist()]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if hasattr(obj, "model_dump"):
        return to_jsonable(obj.model_dump(mode="python"))
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"not canonical-JSON serializable: {type(obj)!r}")


def canonical_json(obj: Any) -> str:
    return json.dumps(
        to_jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class StreamHasher:
    """Incremental SHA-256 over canonical JSON lines (event stream, ledger)."""

    def __init__(self) -> None:
        self._h = hashlib.sha256()
        self.count = 0

    def add(self, obj: Any) -> None:
        self._h.update(canonical_json(obj).encode("utf-8"))
        self._h.update(b"\n")
        self.count += 1

    def hexdigest(self) -> str:
        return self._h.hexdigest()


def write_json(path: str | Path, obj: Any, *, canonical: bool = False) -> None:
    """Atomic write (temp file then rename)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if canonical:
        text = canonical_json(obj)
    else:
        text = json.dumps(to_jsonable(obj), sort_keys=True, indent=2, allow_nan=False)
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: str | Path, rows: list[Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(canonical_json(r))
            fh.write("\n")
    tmp.replace(path)
