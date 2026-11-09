#!/usr/bin/env python3
"""Fails if any file listed in tests/FROZEN.txt changed or is missing (SPEC 18.1).

FROZEN.txt lines: "<sha256>  <path relative to repo root>". Before the freeze commit the
file may be absent, in which case the check passes and says so.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "tests" / "FROZEN.txt"


def main() -> int:
    if not FROZEN.exists():
        print("FROZEN.txt absent: no frozen tests yet")
        return 0
    bad = []
    n = 0
    for line in FROZEN.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        p = ROOT / rel
        n += 1
        if not p.exists():
            bad.append(f"missing: {rel}")
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            bad.append(f"changed: {rel}")
    if bad:
        print("FROZEN TEST CHECK FAILED")
        print("\n".join(bad))
        return 1
    print(f"frozen tests OK ({n} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
