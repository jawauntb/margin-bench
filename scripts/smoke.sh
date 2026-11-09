#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen --extra test
uv run marginbench validate --config configs/default.yaml
uv run marginbench smoke --config configs/default.yaml
