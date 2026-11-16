#!/usr/bin/env bash
# One night of Track M (docs/TRACK-M.md section 4), run by the scheduled task after the close.
# Checks out the append-only `markets-ledger` branch in a worktree, runs the nightly, commits what
# it wrote and pushes. Exit 4 (a symbol's fetch failed) still commits: the hold is in the receipt.
#   scripts/markets_nightly.sh [--private DIR]
set -uo pipefail
cd "$(dirname "$0")/.."
WT=${MARKETS_LEDGER_DIR:-../margin-bench-ledger}
uv sync --frozen --extra test -q || exit 1
git fetch -q origin markets-ledger || exit 1
[ -d "$WT/.git" ] || [ -f "$WT/.git" ] || git worktree add -q "$WT" origin/markets-ledger || exit 1
(cd "$WT" && git checkout -q -B markets-ledger origin/markets-ledger) || exit 1
uv run marginbench markets nightly --ledger "$WT" "$@"; e=$?
[ "$e" -eq 0 ] || [ "$e" -eq 4 ] || { echo "nightly failed (exit $e); nothing committed" >&2; exit "$e"; }
cd "$WT"
git add -A
git diff --cached --quiet && { echo "nothing new"; exit 0; }
git commit -q -m "nightly $(date -u +%Y-%m-%dT%H:%MZ): $(python3 -c 'import json,glob;r=json.load(open(sorted(glob.glob("receipts/*.json"))[-1]));print(r["written"], "holds", list(r["holds"]))')"
for i in 1 2 3 4; do git push -q origin markets-ledger && exit 0; sleep $((2**i)); done
echo "push failed" >&2; exit 1
