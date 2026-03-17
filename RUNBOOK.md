# RUNBOOK.md

## 适用范围
- `dbt-mcp` 是 dbt Labs MCP Server 的本地改造版本，负责向 AI 暴露 dbt 与 MetricFlow 相关工具能力。（状态: 已验证，来源: dbt-mcp/README.md；dbt-mcp/CURRENT_STATE.md）
- 本手册聚焦最小排障与默认自检，不替代 `README.md`、`pyproject.toml` 与 `pr/` 中的需求上下文。（状态: 已验证，来源: AI_CONVENTIONS.md）

## 关键入口
- `bash scripts/doctor.sh`：检查 Python、`uv`、关键目录与核心环境变量提示。（状态: 已验证，来源: 本次第 3 阶段新增脚本；2026-03-17 当前环境执行通过）
- `bash scripts/smoke.sh`：默认通过 `uv` 携带 `dev` 依赖组执行 `tests/unit/test_main.py`，确认入口与配置错误处理的最小链路可用。（状态: 已验证，来源: 本次第 3 阶段新增脚本；2026-03-17 当前环境执行通过，`4 passed, 19 warnings`）
- `dbt-mcp`：启动 MCP Server。（状态: 未验证，来源: dbt-mcp/pyproject.toml；dbt-mcp/README.md）
- `pytest`：完整测试入口。（状态: 未验证，来源: dbt-mcp/pyproject.toml）

## 最小排障顺序
1. 先执行 `bash scripts/doctor.sh`，确认 Python、关键路径和环境变量模型是否就绪。
2. 执行 `bash scripts/smoke.sh`，先验证入口函数和配置错误处理。
3. 如果 `smoke` 通过，再根据实际场景补齐 `DBT_PROJECT_ROOT_DIR`、`DBT_PATH`、`MF_PATH` 并启动 `dbt-mcp`。
4. 如果服务启动失败，优先检查 transport、host/port、API Key 与多项目根目录模型。

## Doctor 重点检查
- `python` 是否可执行。
- `pyproject.toml`、`src/dbt_mcp/config/`、`tests/unit/test_main.py` 是否存在。
- `DBT_PROJECT_ROOT_DIR`、`DBT_PATH`、`MF_PATH`、`MCP_TRANSPORT`、`FASTMCP_HOST`、`FASTMCP_PORT`、`DBT_MCP_API_KEY` 是否已设置。
- 环境变量缺失不一定阻断默认 `smoke`，但会影响真实服务启动与远程模式。

## Smoke 默认做什么
- 默认执行 `uv run --group dev python -m pytest tests/unit/test_main.py -q`。（状态: 已验证，来源: `dbt-mcp/tests/unit/test_main.py`；2026-03-17 当前环境执行通过，`4 passed, 19 warnings`）
- 该文件只覆盖入口函数、配置错误处理与优雅退出逻辑，是 `dbt-mcp` 默认最小自检的合适入口。
- 如果改动涉及 `src/dbt_mcp/config/`、多项目路径或传输层，默认 `smoke` 之后应追加更多单测或本地启动验证。

## 常见失败与判断
- `DBT_PROJECT_ROOT_DIR` 缺失或路径不存在：真实服务启动常见失败原因之一。（状态: 已验证，来源: dbt-mcp/pr/04-问题与修复索引.md）
- `DBT_PATH` / `MF_PATH` 不可执行：会影响 CLI 工具装配，即便代码本身没有回归。
- `MCP_TRANSPORT` 非法：优先怀疑环境变量配置，而不是先怀疑服务主逻辑。
- `smoke` 失败：优先看入口、配置与异常处理是否回归，再扩大到完整 test suite。

## 外部依赖与升级验证建议
- 默认 `smoke` 不会访问真实 dbt 项目，也不会验证远程 HTTP/SSE 服务，只覆盖本地最小入口。
- 涉及 `src/dbt_mcp/config/`、多项目路径模型、远程 transport 或 MetricFlow CLI 包装时，默认 `smoke` 之后应追加更深的配置和服务验证。（状态: 已验证，来源: dbt-mcp/CURRENT_STATE.md）
- 后续如果补 `make doctor` / `make smoke`，应继续保持现有脚本语义稳定，而不是让入口再次分裂。（状态: 推断，来源: 本轮治理目标）
