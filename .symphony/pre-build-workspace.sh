#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

printf '[INFO] prewarming Python workspace with uv sync --frozen --group dev\n'
uv sync --frozen --group dev
