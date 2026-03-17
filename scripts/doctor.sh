#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FAILURES=0

check_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    echo "[OK] command found: $name"
  else
    echo "[FAIL] command missing: $name"
    FAILURES=$((FAILURES + 1))
  fi
}

check_path() {
  local rel="$1"
  if [ -e "$ROOT_DIR/$rel" ]; then
    echo "[OK] path found: $rel"
  else
    echo "[FAIL] path missing: $rel"
    FAILURES=$((FAILURES + 1))
  fi
}

warn_env() {
  local name="$1"
  local note="$2"
  if [ -n "${!name:-}" ]; then
    echo "[OK] env present: $name"
  else
    echo "[WARN] env missing: $name ($note)"
  fi
}

echo "[INFO] dbt-mcp doctor"
echo "[INFO] repo: $ROOT_DIR"

check_cmd python
check_cmd uv

check_path pyproject.toml
check_path src/dbt_mcp/config
check_path tests/unit/test_main.py

warn_env DBT_PROJECT_ROOT_DIR "required for dbt and MetricFlow CLI tools"
warn_env DBT_PATH "required when dbt CLI tools are enabled"
warn_env MF_PATH "required when MetricFlow tools are enabled"
warn_env MCP_TRANSPORT "optional; defaults inside settings"
warn_env FASTMCP_HOST "optional; defaults inside settings"
warn_env FASTMCP_PORT "optional; defaults inside settings"
warn_env DBT_MCP_API_KEY "optional; required only when auth is enabled"

if [ "$FAILURES" -gt 0 ]; then
  echo "[FAIL] doctor finished with $FAILURES blocking issue(s)"
  exit 1
fi

echo "[OK] doctor passed"
