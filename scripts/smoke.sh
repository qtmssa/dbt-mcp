#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PREBUILD_SCRIPT="$ROOT_DIR/.symphony/pre-build-workspace.sh"
cd "$ROOT_DIR"

if [ -f "$PREBUILD_SCRIPT" ]; then
  printf '[INFO] running repo prewarm command: %q\n' "bash $PREBUILD_SCRIPT"
  bash "$PREBUILD_SCRIPT"
fi

CMD=(uv run --group dev python -m pytest tests/unit/test_main.py -q)

if [ "$#" -gt 0 ]; then
  CMD+=("$@")
fi

printf '[INFO] running smoke command:'
printf ' %q' "${CMD[@]}"
printf '\n'
"${CMD[@]}"
