import json
import os
import subprocess
from collections.abc import Iterable
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dbt_mcp.config.config import DbtCliConfig
from dbt_mcp.dbt_cli.binary_type import get_color_disable_flag
from dbt_mcp.dbt_cli.models.lineage_types import ModelLineage
from dbt_mcp.dbt_cli.models.manifest import Manifest
from dbt_mcp.prompts.prompts import get_prompt
from dbt_mcp.project_paths import resolve_project_dir
from dbt_mcp.tools.annotations import create_tool_annotations
from dbt_mcp.tools.definitions import ToolDefinition
from dbt_mcp.tools.fields import (
    DEPTH_FIELD,
    PROJECT_PATH_FIELD,
    TYPES_FIELD,
    UNIQUE_ID_REQUIRED_FIELD,
)
from dbt_mcp.tools.parameters import LineageResourceType
from dbt_mcp.tools.register import register_tools
from dbt_mcp.tools.tool_names import ToolName
from dbt_mcp.tools.toolsets import Toolset


def create_dbt_cli_tool_definitions(config: DbtCliConfig) -> list[ToolDefinition]:
    def _run_dbt_command(
        command: list[str],
        project_path: str,
        selector: str | None = None,
        resource_type: list[str] | None = None,
        is_selectable: bool = False,
        is_full_refresh: bool | None = False,
        vars: str | None = None,
    ) -> str:
        try:
            # Commands that should always be quiet to reduce output verbosity
            verbose_commands = [
                "build",
                "compile",
                "docs",
                "parse",
                "run",
                "test",
                "list",
            ]

            if is_full_refresh is True:
                command.append("--full-refresh")

            if vars and isinstance(vars, str):
                command.extend(["--vars", vars])

            if selector:
                selector_params = str(selector).split(" ")
                command.extend(["--select"] + selector_params)

            if isinstance(resource_type, Iterable):
                command.extend(["--resource-type"] + resource_type)

            full_command = command.copy()
            # Add --quiet flag to specific commands to reduce context window usage
            if len(full_command) > 0 and full_command[0] in verbose_commands:
                main_command = full_command[0]
                command_args = full_command[1:] if len(full_command) > 1 else []
                full_command = [main_command, "--quiet", *command_args]

            project_dir = resolve_project_dir(
                config.project_root_dir,
                project_path,
            )
            cwd_path = str(project_dir)

            # Add appropriate color disable flag based on binary type
            color_flag = get_color_disable_flag(config.binary_type)
            args = [config.dbt_path, color_flag, *full_command]

            process = subprocess.Popen(
                args=args,
                cwd=cwd_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
            )
            output, _ = process.communicate(timeout=config.dbt_cli_timeout)
            return output or "OK"
        except subprocess.TimeoutExpired:
            return "Timeout: dbt command took too long to complete." + (
                " Try using a specific selector to narrow down the results."
                if is_selectable
                else ""
            )

    def _run_dbt_raw_command(
        command_args: list[str],
        project_path: str,
    ) -> str:
        try:
            project_dir = resolve_project_dir(
                config.project_root_dir,
                project_path,
            )
            cwd_path = str(project_dir)

            color_flag = get_color_disable_flag(config.binary_type)
            args = [config.dbt_path, color_flag, *command_args]

            process = subprocess.Popen(
                args=args,
                cwd=cwd_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
            )
            output, _ = process.communicate(timeout=config.dbt_cli_timeout)
            return output or "OK"
        except subprocess.TimeoutExpired:
            return "Timeout: dbt command took too long to complete."

    def build(
        project_path: str = PROJECT_PATH_FIELD,
        selector: str | None = Field(
            default=None, description=get_prompt("dbt_cli/args/selectors")
        ),
        is_full_refresh: bool | None = Field(
            default=None, description=get_prompt("dbt_cli/args/full_refresh")
        ),
        vars: str | None = Field(
            default=None, description=get_prompt("dbt_cli/args/vars")
        ),
    ) -> str:
        return _run_dbt_command(
            ["build"],
            project_path,
            selector,
            is_selectable=True,
            is_full_refresh=is_full_refresh,
            vars=vars,
        )

    def compile(
        project_path: str = PROJECT_PATH_FIELD,
    ) -> str:
        return _run_dbt_command(["compile"], project_path)

    def docs(
        project_path: str = PROJECT_PATH_FIELD,
    ) -> str:
        return _run_dbt_command(["docs", "generate"], project_path)

    def ls(
        project_path: str = PROJECT_PATH_FIELD,
        selector: str | None = Field(
            default=None, description=get_prompt("dbt_cli/args/selectors")
        ),
        resource_type: list[str] | None = Field(
            default=None,
            description=get_prompt("dbt_cli/args/resource_type"),
        ),
    ) -> str:
        return _run_dbt_command(
            ["list"],
            project_path,
            selector,
            resource_type=resource_type,
            is_selectable=True,
        )

    def parse(
        project_path: str = PROJECT_PATH_FIELD,
    ) -> str:
        return _run_dbt_command(["parse"], project_path)

    def run(
        project_path: str = PROJECT_PATH_FIELD,
        selector: str | None = Field(
            default=None, description=get_prompt("dbt_cli/args/selectors")
        ),
        is_full_refresh: bool | None = Field(
            default=None, description=get_prompt("dbt_cli/args/full_refresh")
        ),
        vars: str | None = Field(
            default=None, description=get_prompt("dbt_cli/args/vars")
        ),
    ) -> str:
        return _run_dbt_command(
            ["run"],
            project_path,
            selector,
            is_selectable=True,
            is_full_refresh=is_full_refresh,
            vars=vars,
        )

    def test(
        project_path: str = PROJECT_PATH_FIELD,
        selector: str | None = Field(
            default=None, description=get_prompt("dbt_cli/args/selectors")
        ),
        vars: str | None = Field(
            default=None, description=get_prompt("dbt_cli/args/vars")
        ),
    ) -> str:
        return _run_dbt_command(
            ["test"],
            project_path,
            selector,
            is_selectable=True,
            vars=vars,
        )

    def show(
        project_path: str = PROJECT_PATH_FIELD,
        sql_query: str = Field(description=get_prompt("dbt_cli/args/sql_query")),
        limit: int = Field(default=5, description=get_prompt("dbt_cli/args/limit")),
    ) -> str:
        args = ["show", "--inline", sql_query, "--favor-state"]
        # This is quite crude, but it should be okay for now
        # until we have a dbt Fusion integration.
        cli_limit = None
        if "limit" in sql_query.lower():
            # When --limit=-1, dbt won't apply a separate limit.
            cli_limit = -1
        elif limit:
            # This can be problematic if the LLM provides
            # a SQL limit and a `limit` argument. However, preferencing the limit
            # in the SQL query leads to a better experience when the LLM
            # makes that mistake.
            cli_limit = limit
        if cli_limit is not None:
            args.extend(["--limit", str(cli_limit)])
        args.extend(["--output", "json"])
        return _run_dbt_command(args, project_path)

    def execute_dbt_cmd(
        project_path: str = PROJECT_PATH_FIELD,
        command_args: list[str] = Field(
            description=get_prompt("dbt_cli/args/command_args")
        ),
    ) -> str:
        return _run_dbt_raw_command(command_args, project_path)

    def _get_manifest(project_path: str) -> Manifest:
        """Helper function to load the dbt manifest.json file."""
        _run_dbt_command(["parse"], project_path)  # Ensure manifest is generated
        project_dir = resolve_project_dir(
            config.project_root_dir,
            project_path,
        )
        manifest_path = os.path.join(str(project_dir), "target", "manifest.json")
        with open(manifest_path) as f:
            manifest_data = json.load(f)
        return Manifest(**manifest_data)

    def get_lineage_dev(
        project_path: str = PROJECT_PATH_FIELD,
        unique_id: str = UNIQUE_ID_REQUIRED_FIELD,
        types: list[LineageResourceType] | None = TYPES_FIELD,
        depth: int = DEPTH_FIELD,
    ) -> dict[str, Any]:
        manifest = _get_manifest(project_path)
        model_lineage = ModelLineage.from_manifest(
            manifest,
            unique_id=unique_id,
            types=types,
            depth=depth,
        )
        return model_lineage.model_dump()

    def get_node_details_dev(
        project_path: str = PROJECT_PATH_FIELD,
        node_id: str = Field(
            description=get_prompt("dbt_cli/args/node_id"),
        ),
    ) -> dict[str, Any]:
        # Comprehensive list of output keys to include all available node metadata
        output_keys = [
            # This is the entire list. Keeping it for ref and commmenting fields that are not needed.
            # Because we get the path, we should not need the raw_code and compiled_code that can be very big and that the LLM can read
            "unique_id",
            "name",
            "resource_type",
            "package_name",
            "original_file_path",
            "path",
            "alias",
            "description",
            "columns",
            "meta",
            "tags",
            "config",
            "depends_on",
            "patch_path",
            "schema",
            "database",
            "relation_name",
            # "raw_code",
            # "compiled_code",
            # "checksum",
            "language",
            "docs",
            "group",
            "access",
            "version",
            "latest_version",
            "deprecation_date",
            "contract",
            "constraints",
            "primary_key",
            "fqn",
            "build_path",
            "refs",
            "sources",
            "metrics",
            "created_at",
            "unrendered_config",
        ]
        output = _run_dbt_command(
            ["list", "--output", "json", "--output-keys", *output_keys],
            project_path,
            selector=node_id,
            is_selectable=True,
        )

        node_result: dict[str, Any] | None = None
        test_ids: list[str] = []

        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                node = json.loads(line)
                resource_type = node.get("resource_type")
                if node_result is None:
                    # First node is the primary result
                    node_result = node
                elif resource_type == "test":
                    # Collect additional tests (associated with the primary node)
                    fqn = node.get("fqn", [])
                    test_ids.append(".".join(fqn) if fqn else node.get("unique_id", ""))
            except json.JSONDecodeError:
                continue

        if node_result is None:
            raise ValueError(f"No node found for selector: {node_id}")

        # Add test unique_ids for models, seeds, sources, and snapshots
        if node_result.get("resource_type") in ("model", "seed", "source", "snapshot"):
            node_result["tests"] = test_ids

        return node_result

    return [
        ToolDefinition(
            fn=build,
            description=get_prompt("dbt_cli/build"),
            annotations=create_tool_annotations(
                title="dbt build",
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=False,
            ),
        ),
        ToolDefinition(
            fn=compile,
            description=get_prompt("dbt_cli/compile"),
            annotations=create_tool_annotations(
                title="dbt compile",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            fn=docs,
            description=get_prompt("dbt_cli/docs"),
            annotations=create_tool_annotations(
                title="dbt docs",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            name="list",
            fn=ls,
            description=get_prompt("dbt_cli/list"),
            annotations=create_tool_annotations(
                title="dbt list",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            fn=parse,
            description=get_prompt("dbt_cli/parse"),
            annotations=create_tool_annotations(
                title="dbt parse",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            fn=run,
            description=get_prompt("dbt_cli/run"),
            annotations=create_tool_annotations(
                title="dbt run",
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=False,
            ),
        ),
        ToolDefinition(
            fn=test,
            description=get_prompt("dbt_cli/test"),
            annotations=create_tool_annotations(
                title="dbt test",
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=False,
            ),
        ),
        ToolDefinition(
            fn=show,
            description=get_prompt("dbt_cli/show"),
            annotations=create_tool_annotations(
                title="dbt show",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            fn=execute_dbt_cmd,
            description=get_prompt("dbt_cli/execute_dbt_cmd"),
            annotations=create_tool_annotations(
                title="dbt execute",
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=False,
            ),
        ),
        ToolDefinition(
            name="get_lineage_dev",
            fn=get_lineage_dev,
            description=get_prompt("dbt_cli/get_lineage_dev"),
            annotations=create_tool_annotations(
                title="Get Model Lineage (Dev)",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            name="get_node_details_dev",
            fn=get_node_details_dev,
            description=get_prompt("dbt_cli/get_node_details_dev"),
            annotations=create_tool_annotations(
                title="Get Node Details (Dev)",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
    ]


def register_dbt_cli_tools(
    dbt_mcp: FastMCP,
    config: DbtCliConfig,
    *,
    disabled_tools: set[ToolName],
    enabled_tools: set[ToolName] | None,
    enabled_toolsets: set[Toolset],
    disabled_toolsets: set[Toolset],
) -> None:
    register_tools(
        dbt_mcp,
        tool_definitions=create_dbt_cli_tool_definitions(config),
        disabled_tools=disabled_tools,
        enabled_tools=enabled_tools,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
    )
