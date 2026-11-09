"""Run provenance: code commit, dirty flag, lock hash, platform (SPEC 17.4)."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from marginbench.config import REPO_ROOT
from marginbench.hashing import file_sha256


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""


def code_state() -> dict[str, Any]:
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=no", "--", "src", "configs", "models", "tests", "scripts",
                     "pyproject.toml", "uv.lock"))
    return {"git_commit": commit or "unknown", "dirty": dirty}


def lock_hash() -> str:
    for name in ("uv.lock", "requirements.lock"):
        p = Path(REPO_ROOT) / name
        if p.exists():
            return file_sha256(p)
    return "missing"


def environment_info() -> dict[str, Any]:
    return {"python": sys.version.split()[0], "platform": platform.platform(), "lock_hash": lock_hash()}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
