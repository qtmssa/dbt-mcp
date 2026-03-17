# CURRENT_STATE.md

## 项目定位
- `dbt-mcp` 是 dbt Labs MCP Server 的本地改造版本，用于让 dbt Core、dbt Fusion / MetricFlow、dbt Platform 以 MCP 形式向 AI 共享上下文与工具能力。（状态: 已验证，来源: dbt-mcp/README.md；dbt-mcp/pr/00-项目基线.md）
- 当前仓库本地重点围绕 dbt CLI 与 MetricFlow CLI 封装、项目文件工具、远程服务模式以及多项目根目录与 `project_path` 模型。（状态: 已验证，来源: dbt-mcp/pr/00-项目基线.md；dbt-mcp/pr/01-当前有效需求索引.md）

## 当前主要目标
- 将 MetricFlow CLI 的常用命令封装为 MCP 工具，并保持与 dbt CLI 类似的使用体验。（状态: 已验证，来源: dbt-mcp/pr/01-当前有效需求索引.md）
- 补齐 MetricFlow 项目文件工具、工具说明与远程服务运行模式，明确 transport、host、port 与 API Key 鉴权配置。（状态: 已验证，来源: dbt-mcp/pr/01-当前有效需求索引.md）
- 重构 `DBT_PROJECT_ROOT_DIR + project_path` 多项目模型，并同步修复 pytest、编码与运行时兼容问题。（状态: 已验证，来源: dbt-mcp/pr/01-当前有效需求索引.md）

## 当前重点
- 继续推进 MetricFlow CLI 与 dbt CLI 的 MCP 包装，包括工具描述、参数说明以及本地/远程模式的统一表达。（状态: 已验证，来源: dbt-mcp/pr/01-当前有效需求索引.md）
- 梳理 `MCP_TRANSPORT`、`FASTMCP_HOST`、`FASTMCP_PORT`、`DBT_MCP_API_KEY` 等参数对服务启动和远程部署的影响。（状态: 已验证，来源: dbt-mcp/README.md；dbt-mcp/pr/01-当前有效需求索引.md）
- 细化多项目路径模型与测试环境的一致性，避免用例依赖不存在的根目录或隐藏环境变量假设。（状态: 已验证，来源: dbt-mcp/pr/04-问题与修复索引.md）
- 修补 pytest async、编码与旧版本兼容链路，让 `pytest` 成为稳定的最小回归入口。（状态: 已验证，来源: dbt-mcp/pr/01-当前有效需求索引.md）

## 最近一次可用的最小验证方式
- `bash scripts/doctor.sh`（状态: 已验证，来源: dbt-mcp/RUNBOOK.md；2026-03-17 当前环境执行通过）
- `bash scripts/smoke.sh`（状态: 未验证，来源: dbt-mcp/RUNBOOK.md）
- `dbt-mcp`（状态: 未验证，来源: dbt-mcp/pyproject.toml；dbt-mcp/README.md）
- `pytest`（状态: 未验证，来源: dbt-mcp/pyproject.toml）

## 已知阻塞/高风险区域
- `src/dbt_mcp/config` 是配置解析与环境变量装配核心，涉及 `MCP_TRANSPORT`、`FASTMCP_*`、`DBT_*`、`MF_*` 等参数。（状态: 已验证，来源: 目录实际结构；dbt-mcp/README.md）
- 多项目路径模型及其与 `DBT_PATH`、`MF_PATH`、`DBT_PROJECT_ROOT_DIR`、`project_path` 的配合仍在重构中，路径不存在就会直接报错。（状态: 已验证，来源: dbt-mcp/pr/04-问题与修复索引.md）
- `dbt-core`、`dbt-metricflow`、`dbt-postgres` 与 pytest 兼容性共同决定本地可用性，依赖或环境不一致容易反复引发运行期问题。（状态: 已验证，来源: dbt-mcp/pyproject.toml；dbt-mcp/pr/01-当前有效需求索引.md）

## 当前不建议碰的区域
- 在没有明确需求时，不建议先改 `examples/` 中面向外部 agent 的示例配置，以免与文档或外部使用方式脱节。（状态: 推断，来源: dbt-mcp/README.md；目录实际结构）
- `uv.lock` 与 `pyproject.toml` 的依赖组合当前用于支撑兼容性修复主线，非必要不要单独调整锁文件或大幅改依赖集合。（状态: 推断，来源: dbt-mcp/pyproject.toml）

## 首读顺序
1. `dbt-mcp/README.md`（状态: 已验证，来源: 文件存在）
2. `dbt-mcp/pyproject.toml`（状态: 已验证，来源: 文件存在）
3. `dbt-mcp/RUNBOOK.md`（状态: 已验证，来源: 文件存在）
4. `dbt-mcp/pr/01-当前有效需求索引.md`（状态: 已验证，来源: 文件存在）
5. `dbt-mcp/pr/00-项目基线.md`（状态: 已验证，来源: 文件存在）
6. `dbt-mcp/pr/04-问题与修复索引.md`（状态: 已验证，来源: 文件存在）
7. `dbt-mcp/src/dbt_mcp/config/`（状态: 已验证，来源: 目录存在）

## 备注
- 本文件只做项目当前状态入口，不替代 README 与需求索引；后续若补 `RUNBOOK.md` 或 doctor/smoke，应继续沿用“已验证 / 未验证 / 推断”标记。（状态: 已验证，来源: AI_CONVENTIONS.md）
- 当前阶段已补 `RUNBOOK.md` 与最小 `doctor/smoke` 入口，排障时应先用这两个脚本确认本地配置和入口函数，再扩大到完整服务启动。（状态: 已验证，来源: 本次第 3 阶段落地结果）
