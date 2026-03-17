#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

CMD=(uv run --group dev python -m pytest tests/unit/test_main.py -q)

if [ "$#" -gt 0 ]; then
  CMD+=("$@")
fi

printf '[INFO] running smoke command:'
printf ' %q' "${CMD[@]}"
printf '\n'
"${CMD[@]}"
