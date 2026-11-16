"""Write a test receipt: what ran, what testonce skipped and why that is safe, on which tree.

A receipt is evidence that a given working tree passed: the HEAD commit, a hash of every change
on top of it (staged, unstaged and untracked), each file's outcome (ran and passed, skipped on a
recorded pass with identical inputs, failed), the totals and the tool versions. It lands in
receipts/tests/<UTC time>-<head>.json and is committed with the change it covers.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except Exception:  # noqa: BLE001
        return ""


def tree_state() -> str:
    """sha256 over the diff against HEAD and every untracked file's bytes: the exact tree tested."""
    h = hashlib.sha256(git("diff", "HEAD", "--binary").encode())
    for name in sorted(git("ls-files", "--others", "--exclude-standard").split("\n")):
        p = ROOT / name
        if name and p.is_file() and not name.startswith("receipts/"):
            h.update(name.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("testonce", "plain"), required=True)
    ap.add_argument("--exit", type=int, required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--reason", default=None)
    a = ap.parse_args()
    log = Path(a.log).read_text(errors="replace")
    files = {m[1]: m[0] for m in re.findall(r"^testonce: (pass|skip|fail\w*) (\S+)$", log, re.M)}
    total = re.findall(r"^testonce: (\d+) files: (\d+) skipped, (\d+) ran, (\d+) failed$", log, re.M)
    plain = re.findall(r"^(\d+) passed.*$", log, re.M)
    head = git("rev-parse", "HEAD").strip()
    now = dt.datetime.now(dt.timezone.utc)
    receipt = {
        "v": 1, "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": a.mode, "reason": a.reason,
        "exit": a.exit, "passed": a.exit == 0, "head": head or None, "branch": git("branch", "--show-current").strip(),
        "tree_state_sha256": tree_state(), "files": dict(sorted(files.items())),
        "totals": dict(zip(("files", "skipped", "ran", "failed"), map(int, total[-1]))) if total else None,
        "plain_passed": int(plain[-1]) if plain else None,
        "python": platform.python_version(),
        "testonce": git("-C", str(ROOT.parent / "testonce"), "rev-parse", "HEAD").strip() or None,
        "skip_rule": "a file is skipped only when every input it read, every program it ran and every "
                     "environment variable is byte-identical to a recorded pass (testonce, proved in Lean 4)",
    }
    out = ROOT / "receipts" / "tests" / f"{now:%Y%m%dT%H%M%SZ}-{(head or 'nohead')[:9]}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    t = receipt["totals"]
    print(f"receipt {out.relative_to(ROOT)}: {'PASS' if receipt['passed'] else 'FAIL'}"
          + (f", {t['ran']} ran, {t['skipped']} skipped" if t else ""))


if __name__ == "__main__":
    main()
