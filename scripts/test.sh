#!/usr/bin/env bash
# The repo's test command (AGENTS rule 6): every pytest file through testonce (jawauntb/testonce,
# free core). A file whose every input (files read, programs run, environment) is byte-identical to
# a recorded pass is skipped with that pass; anything changed, or anything testonce cannot vouch
# for, runs. `python -m pytest -q` remains the reference; with no node or strace, or if testonce
# itself fails, this runs it and says so, so the command never silently weakens.
#
# Every run writes a receipt: receipts/tests/<UTC time>-<head>.json (scripts/test_receipt.py).
#   scripts/test.sh            all test files
#   scripts/test.sh FILE...    only these files
set -uo pipefail
cd "$(dirname "$0")/.."
PY=python; [ -x .venv/bin/python ] && PY=.venv/bin/python   # not `uv run`: its lock files churn
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

mapfile -t files < <(if [ $# -gt 0 ]; then printf '%s\n' "$@"; else find tests -name 'test_*.py' | sort; fi)

run_plain() {
  echo "test.sh: $1; running plain pytest" >&2
  "$PY" -m pytest -q "$@" 2>&1 | tee "$LOG"; local e=${PIPESTATUS[0]}
  "$PY" scripts/test_receipt.py --mode plain --reason "$1" --exit "$e" --log "$LOG"
  exit "$e"
}

command -v node >/dev/null || run_plain "no node"
command -v strace >/dev/null || run_plain "no strace"
if [ -n "${TESTONCE:-}" ]; then T=(node "$TESTONCE")
elif command -v testonce >/dev/null; then T=(testonce)
elif [ -f ../testonce/bin/testonce.mjs ]; then T=(node ../testonce/bin/testonce.mjs)
else T=(npx -y github:jawauntb/testonce)
fi

"${T[@]}" each "${files[@]}" -- sh -c "$PY"' -m pytest -q -p no:cacheprovider "$1"' _ {} 2>&1 | tee "$LOG"
e=${PIPESTATUS[0]}
[ "$e" -eq 0 ] || run_plain "testonce failed (exit $e)"
"$PY" scripts/test_receipt.py --mode testonce --exit 0 --log "$LOG"
