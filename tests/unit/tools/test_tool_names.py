from unittest.mock import patch

from dbt_mcp.config.config import load_config
from dbt_mcp.dbt_cli.binary_type import BinaryType
from dbt_mcp.lsp.lsp_binary_manager import LspBinaryInfo
from dbt_mcp.mcp.server import create_dbt_mcp
from dbt_mcp.tools.register import should_register_tool
from dbt_mcp.tools.tool_names import ToolName
from dbt_mcp.tools.toolsets import TOOL_TO_TOOLSET, proxied_tools


async def test_tool_names_match_server_tools(env_setup):
    """Test that the ToolName enum matches the tools registered in the server."""
    with (
        env_setup(
            env_vars={
                "DISABLE_DBT_CODEGEN": "false",
                "DISABLE_MCP_SERVER_METADATA": "false",
            }
        ),
        patch(
            "dbt_mcp.config.config.detect_binary_type", return_value=BinaryType.DBT_CORE
        ),
        patch(
            "dbt_mcp.config.config.dbt_lsp_binary_info",
            return_value=LspBinaryInfo(path="/path/to/lsp", version="1.0.0"),
        ),
    ):
        config = load_config(enable_proxied_tools=False)
        dbt_mcp = await create_dbt_mcp(config)

        # Get all tools from the server
        server_tools = await dbt_mcp.list_tools()
        enabled_tools = set(config.enable_tools) if config.enable_tools is not None else None
        disabled_tools = set(config.disable_tools or [])
        enabled_toolsets = config.enabled_toolsets
        disabled_toolsets = config.disabled_toolsets

        # Manually add proxied tools only if they'd be enabled by filters
        expected_proxied = {
            p.value
            for p in proxied_tools
            if should_register_tool(
                tool_name=p,
                enabled_tools=enabled_tools,
                disabled_tools=disabled_tools,
                enabled_toolsets=enabled_toolsets,
                disabled_toolsets=disabled_toolsets,
                tool_to_toolset=TOOL_TO_TOOLSET,
            )
        }
        server_tool_names = {tool.name for tool in server_tools} | expected_proxied
        enum_names = {
            tool.value
            for tool in ToolName
            if should_register_tool(
                tool_name=tool,
                enabled_tools=enabled_tools,
                disabled_tools=disabled_tools,
                enabled_toolsets=enabled_toolsets,
                disabled_toolsets=disabled_toolsets,
                tool_to_toolset=TOOL_TO_TOOLSET,
            )
        }

        # This should not raise any errors if the enum is in sync
        if server_tool_names != enum_names:
            raise ValueError(
                f"Tool name mismatch:\n"
                f"In server but not in enum: {server_tool_names - enum_names}\n"
                f"In enum but not in server: {enum_names - server_tool_names}"
            )

        # Double check that all enum values are strings
        for tool in ToolName:
            assert isinstance(tool.value, str), (
                f"Tool {tool.name} value should be a string"
            )


def test_tool_names_no_duplicates():
    """Test that there are no duplicate tool names in the enum."""
    assert len(ToolName.get_all_tool_names()) == len(set(ToolName.get_all_tool_names()))
