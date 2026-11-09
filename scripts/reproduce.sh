#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run marginbench reproduce --manifest results/primary/run_manifest.json
