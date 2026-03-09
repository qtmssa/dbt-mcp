import logging
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from dbt_mcp.config.config import MetricflowConfig
from dbt_mcp.prompts.prompts import get_prompt
from dbt_mcp.project_paths import resolve_project_dir, resolve_project_root
from dbt_mcp.tools.annotations import create_tool_annotations
from dbt_mcp.tools.definitions import ToolDefinition
from dbt_mcp.tools.fields import PROJECT_PATH_FIELD
from dbt_mcp.tools.register import register_tools
from dbt_mcp.tools.tool_names import ToolName
from dbt_mcp.tools.toolsets import Toolset
from tools.metricflow_unzip import unzip_metricflow_zip

logger = logging.getLogger(__name__)


def _resolve_project_dir(
    project_root_dir: Path,
    project_path: str,
    *,
    must_exist: bool = True,
    allow_empty: bool = False,
) -> Path:
    return resolve_project_dir(
        project_root_dir,
        project_path,
        must_exist=must_exist,
        allow_empty=allow_empty,
    )


def create_metricflow_tool_definitions(
    config: MetricflowConfig,
) -> list[ToolDefinition]:
    """Create MetricFlow CLI tool definitions.

    Args:
        config: MetricFlow CLI configuration.

    Returns:
        List of MetricFlow ToolDefinition objects.
    """

    def _run_mf_command(
        command: list[str],
        project_path: str,
        extra_args: list[str] | None = None,
    ) -> str:
        """Run a MetricFlow CLI command.

        Args:
            command: Command tokens excluding the `mf` binary.
            extra_args: Additional CLI arguments to append.

        Returns:
            The command output, or an error message.
        """
        try:
            full_command = list(command)
            if extra_args:
                full_command.extend([str(arg) for arg in extra_args])

            project_dir = _resolve_project_dir(
                config.project_root_dir,
                project_path,
            )
            cwd_path = str(project_dir)

            args = [config.mf_path, *full_command]
            process = subprocess.Popen(
                args=args,
                cwd=cwd_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
            )
            output, _ = process.communicate(timeout=config.mf_cli_timeout)
            if process.returncode != 0:
                return f"Error running mf command: {output}"
            return output or "OK"
        except subprocess.TimeoutExpired:
            return (
                f"Timeout: mf command took longer than {config.mf_cli_timeout} seconds."
            )
        except Exception as e:
            return str(e)

    def health_checks(
        project_path: str = PROJECT_PATH_FIELD,
        extra_args: list[str] | None = Field(
            default=None, description=get_prompt("metricflow/args/extra_args")
        ),
    ) -> str:
        """Run `mf health-checks`.

        Args:
            extra_args: Additional CLI arguments to pass to MetricFlow.

        Returns:
            Command output or error message.
        """
        return _run_mf_command(
            ["health-checks"],
            project_path,
            extra_args=extra_args,
        )

    def mf_list(
        project_path: str = PROJECT_PATH_FIELD,
        extra_args: list[str] | None = Field(
            default=None, description=get_prompt("metricflow/args/extra_args")
        ),
    ) -> str:
        """Run `mf list`.

        Args:
            extra_args: Additional CLI arguments to pass to MetricFlow.

        Returns:
            Command output or error message.
        """
        return _run_mf_command(["list"], project_path, extra_args=extra_args)

    def query(
        project_path: str = PROJECT_PATH_FIELD,
        extra_args: list[str] | None = Field(
            default=None, description=get_prompt("metricflow/args/extra_args")
        ),
    ) -> str:
        """Run `mf query`.

        Args:
            extra_args: Additional CLI arguments to pass to MetricFlow.

        Returns:
            Command output or error message.
        """
        return _run_mf_command(["query"], project_path, extra_args=extra_args)

    def tutorial(
        project_path: str = PROJECT_PATH_FIELD,
        extra_args: list[str] | None = Field(
            default=None, description=get_prompt("metricflow/args/extra_args")
        ),
    ) -> str:
        """Run `mf tutorial`.

        Args:
            extra_args: Additional CLI arguments to pass to MetricFlow.

        Returns:
            Command output or error message.
        """
        return _run_mf_command(["tutorial"], project_path, extra_args=extra_args)

    def validate_configs(
        project_path: str = PROJECT_PATH_FIELD,
        extra_args: list[str] | None = Field(
            default=None, description=get_prompt("metricflow/args/extra_args")
        ),
    ) -> str:
        """Run `mf validate-configs`.

        Args:
            extra_args: Additional CLI arguments to pass to MetricFlow.

        Returns:
            Command output or error message.
        """
        return _run_mf_command(
            ["validate-configs"],
            project_path,
            extra_args=extra_args,
        )

    def execute_mf_cmd(
        project_path: str = PROJECT_PATH_FIELD,
        command_args: list[str] = Field(
            description=get_prompt("metricflow/args/command_args")
        ),
    ) -> str:
        """Run an arbitrary `mf` command."""
        return _run_mf_command(command_args, project_path, extra_args=None)

    def list_projects(
        project_path: str = Field(
            default=".",
            description="Project base path relative to DBT_PROJECT_ROOT_DIR. Use '.' for root.",
        ),
    ) -> list[str]:
        """List available projects under DBT_PROJECT_ROOT_DIR."""
        root = resolve_project_root(config.project_root_dir)
        base_dir = _resolve_project_dir(
            config.project_root_dir,
            project_path,
            allow_empty=True,
        )
        projects: list[str] = []
        if (base_dir / "dbt_project.yml").is_file():
            projects.append(base_dir.relative_to(root).as_posix())
        for child in base_dir.iterdir():
            if child.is_dir() and (child / "dbt_project.yml").is_file():
                projects.append(child.relative_to(root).as_posix())
        return sorted(set(projects))

    def is_project_exist(
        project_path: str = PROJECT_PATH_FIELD,
    ) -> bool:
        """Check whether a project exists under DBT_PROJECT_ROOT_DIR."""
        project_dir = _resolve_project_dir(
            config.project_root_dir,
            project_path,
            must_exist=False,
        )
        if not project_dir.is_dir():
            return False
        return (project_dir / "dbt_project.yml").is_file()

    def _upload_project_zip_url_single(
        project_path: str,
        zip_url: str,
    ) -> dict[str, Any]:
        logger.info(
            "upload_project_zip_url start",
            extra={"project_path": project_path, "zip_url": zip_url},
        )
        root = resolve_project_root(config.project_root_dir)
        target_dir = _resolve_project_dir(
            config.project_root_dir,
            project_path,
            must_exist=False,
        )
        if target_dir == root:
            raise ValueError(
                "project_path must be a subdirectory under DBT_PROJECT_ROOT_DIR."
            )
        if target_dir.exists():
            raise ValueError(f"Project already exists: {project_path}")
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=str(root)) as temp_dir:
            temp_root = Path(temp_dir)
            zip_path = temp_root / "project.zip"
            try:
                with (
                    urllib.request.urlopen(zip_url) as response,
                    zip_path.open("wb") as handle,
                ):
                    shutil.copyfileobj(response, handle)
                zip_size = zip_path.stat().st_size
                logger.info(
                    "zip download completed",
                    extra={"zip_path": str(zip_path), "zip_size_bytes": zip_size},
                )
            except Exception as exc:
                logger.exception("zip download failed", extra={"zip_url": zip_url})
                raise ValueError("Failed to download zip from zip_url.") from exc
            extract_root = temp_root / "extract"
            logger.info(
                "starting unzip",
                extra={"zip_path": str(zip_path), "extract_root": str(extract_root)},
            )
            unzip_result = unzip_metricflow_zip(zip_path, extract_root)
            logger.info(
                "unzip completed",
                extra={"project_root": str(unzip_result.project_root)},
            )
            if target_dir.exists():
                raise ValueError(f"Project already exists: {project_path}")
            shutil.move(str(unzip_result.project_root), str(target_dir))
            logger.info(
                "project moved",
                extra={"project_root": str(target_dir)},
            )

        return {
            "project_path": project_path,
            "project_root": str(target_dir),
        }

    def upload_project_zip_url(
        project_path: str | None = Field(
            default=None,
            description=(
                "Project path relative to DBT_PROJECT_ROOT_DIR. "
                "Required when batch is not provided."
            ),
        ),
        zip_url: str | None = Field(
            default=None,
            description=get_prompt("metricflow/args/zip_url"),
        ),
        batch: list[dict[str, str]] | None = Field(
            default=None,
            description=get_prompt("metricflow/args/zip_url_batch"),
        ),
    ) -> dict[str, Any]:
        """Upload MetricFlow project zip(s) under DBT_PROJECT_ROOT_DIR from URL(s)."""
        if batch:
            results: list[dict[str, Any]] = []
            errors: list[dict[str, Any]] = []
            seen_paths: set[str] = set()
            for idx, item in enumerate(batch):
                item_project_path = item.get("project_path")
                item_zip_url = item.get("zip_url")
                if not item_project_path or not item_zip_url:
                    error = {
                        "index": idx,
                        "error": "batch item requires project_path and zip_url",
                    }
                    errors.append(error)
                    results.append({"success": False, **error})
                    continue
                if item_project_path in seen_paths:
                    error = {
                        "index": idx,
                        "project_path": item_project_path,
                        "error": "duplicate project_path in batch",
                    }
                    errors.append(error)
                    results.append({"success": False, **error})
                    continue
                seen_paths.add(item_project_path)

                try:
                    upload_result = _upload_project_zip_url_single(
                        item_project_path,
                        item_zip_url,
                    )
                    results.append(
                        {
                            "success": True,
                            "project_path": upload_result["project_path"],
                            "project_root": upload_result["project_root"],
                            "zip_url": item_zip_url,
                        }
                    )
                except Exception as exc:
                    logger.exception(
                        "batch upload failed",
                        extra={
                            "project_path": item_project_path,
                            "zip_url": item_zip_url,
                        },
                    )
                    error = {
                        "project_path": item_project_path,
                        "zip_url": item_zip_url,
                        "error": str(exc),
                    }
                    errors.append(error)
                    results.append({"success": False, **error})

            return {
                "success": len(errors) == 0,
                "items": results,
                "errors": errors,
            }

        if not project_path or not zip_url:
            raise ValueError(
                "project_path and zip_url are required when batch is not provided."
            )
        return _upload_project_zip_url_single(project_path, zip_url)

    def delete_project(
        project_path: str = PROJECT_PATH_FIELD,
    ) -> dict[str, Any]:
        """Delete a project directory under DBT_PROJECT_ROOT_DIR."""
        root = resolve_project_root(config.project_root_dir)
        target_dir = _resolve_project_dir(
            config.project_root_dir,
            project_path,
            must_exist=True,
        )
        if target_dir == root:
            raise ValueError(
                "project_path must be a subdirectory under DBT_PROJECT_ROOT_DIR."
            )
        shutil.rmtree(target_dir)
        return {"deleted": project_path}

    return [
        ToolDefinition(
            name="mf.health-checks",
            fn=health_checks,
            description=get_prompt("metricflow/health-checks"),
            annotations=create_tool_annotations(
                title="mf health-checks",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            name="mf.list",
            fn=mf_list,
            description=get_prompt("metricflow/list"),
            annotations=create_tool_annotations(
                title="mf list",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            name="mf.query",
            fn=query,
            description=get_prompt("metricflow/query"),
            annotations=create_tool_annotations(
                title="mf query",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            name="mf.tutorial",
            fn=tutorial,
            description=get_prompt("metricflow/tutorial"),
            annotations=create_tool_annotations(
                title="mf tutorial",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            name="mf.validate-configs",
            fn=validate_configs,
            description=get_prompt("metricflow/validate-configs"),
            annotations=create_tool_annotations(
                title="mf validate-configs",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
            ),
        ),
        ToolDefinition(
            fn=execute_mf_cmd,
            description=get_prompt("metricflow/execute_mf_cmd"),
            annotations=create_tool_annotations(
                title="mf execute",
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=False,
            ),
        ),
        ToolDefinition(
            fn=list_projects,
            description=get_prompt("metricflow/list_projects"),
            annotations=create_tool_annotations(
                title="list_projects",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=False,
            ),
        ),
        ToolDefinition(
            fn=is_project_exist,
            description=get_prompt("metricflow/is_project_exist"),
            annotations=create_tool_annotations(
                title="is_project_exist",
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=False,
            ),
        ),
        ToolDefinition(
            fn=upload_project_zip_url,
            description=get_prompt("metricflow/upload_project_zip_url"),
            annotations=create_tool_annotations(
                title="upload_project_zip_url",
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=False,
                open_world_hint=False,
            ),
        ),
        ToolDefinition(
            fn=delete_project,
            description=get_prompt("metricflow/delete_project"),
            annotations=create_tool_annotations(
                title="delete_project",
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=False,
                open_world_hint=False,
            ),
        ),
    ]


def register_metricflow_tools(
    dbt_mcp: FastMCP,
    config: MetricflowConfig,
    *,
    disabled_tools: set[ToolName],
    enabled_tools: set[ToolName] | None,
    enabled_toolsets: set[Toolset],
    disabled_toolsets: set[Toolset],
) -> None:
    """Register MetricFlow tools with the MCP server.

    Args:
        dbt_mcp: FastMCP server instance.
        config: MetricFlow CLI configuration.
        disabled_tools: Tools to disable explicitly.
        enabled_tools: Tools to enable explicitly.
        enabled_toolsets: Enabled toolsets.
        disabled_toolsets: Disabled toolsets.
    """
    register_tools(
        dbt_mcp,
        tool_definitions=create_metricflow_tool_definitions(config),
        disabled_tools=disabled_tools,
        enabled_tools=enabled_tools,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
    )
