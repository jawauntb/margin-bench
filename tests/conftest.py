"""Session fixture: the frozen-test hash check runs before any test (SPEC 18.1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


@pytest.fixture(scope="session", autouse=True)
def frozen_tests_unchanged() -> None:
    res = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_frozen_tests.py")],
                         capture_output=True, text=True)
    if res.returncode != 0:
        pytest.exit(f"frozen-test hash check failed:\n{res.stdout}{res.stderr}", returncode=3)
