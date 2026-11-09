#!/usr/bin/env bash
# Locked, preregistered evaluation. Refuses to run on a dirty tree or a changed plan/estimator.
set -euo pipefail
cd "$(dirname "$0")/.."
W=${WORKERS:-4}
uv run marginbench evaluate --plan configs/plan.yaml --output results/primary --workers "$W"
for e in E1 E2 E3 E4 E5 E6 E7 E-DEPLOY P6-DIAG; do
  uv run marginbench experiment --id "$e" --output "results/$e" --workers "$W"
done
uv run marginbench ablate --output results/ablations --workers "$W"
uv run marginbench experiment --id E9 --output results/e9 --workers "$W"
uv run marginbench experiment --id E8 --output results/E8 --workers "$W"
uv run marginbench sensitivity --output results/sensitivity --workers "$W"
uv run marginbench audit --results results
