import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from dbtlabs_vortex.producer import shutdown
from mcp.server.fastmcp import FastMCP
from mcp.server.lowlevel.server import LifespanResultT
from mcp.server.auth.settings import AuthSettings
from mcp.types import ContentBlock, TextContent

from dbt_mcp.config.config import Config
from dbt_mcp.dbt_admin.tools import register_admin_api_tools
from dbt_mcp.dbt_cli.tools import register_dbt_cli_tools
from dbt_mcp.dbt_codegen.tools import register_dbt_codegen_tools
from dbt_mcp.discovery.tools import register_discovery_tools
from dbt_mcp.metricflow.tools import register_metricflow_tools
from dbt_mcp.mcp_server_metadata.tools import register_mcp_server_tools
from dbt_mcp.lsp.providers.project_lsp_client_provider import (
    ProjectLSPClientProvider,
)
from dbt_mcp.lsp.tools import register_lsp_tools
from dbt_mcp.mcp.api_key_auth import ApiKeyTokenVerifier
from dbt_mcp.proxy.tools import ProxiedToolsManager, register_proxied_tools
from dbt_mcp.semantic_layer.client import DefaultSemanticLayerClientProvider
from dbt_mcp.semantic_layer.tools import register_sl_tools
from dbt_mcp.tracking.tracking import DefaultUsageTracker, ToolCalledEvent, UsageTracker

logger = logging.getLogger(__name__)


class DbtMCP(FastMCP):
    def __init__(
        self,
        config: Config,
        usage_tracker: UsageTracker,
        lifespan: (
            Callable[
                [FastMCP[LifespanResultT]], AbstractAsyncContextManager[LifespanResultT]
            ]
            | None
        ),
        lsp_client_provider: ProjectLSPClientProvider | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs, lifespan=lifespan)
        self.usage_tracker = usage_tracker
        self.config = config
        self.lsp_client_provider = lsp_client_provider

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> Sequence[ContentBlock] | dict[str, Any]:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        result = None
        start_time = int(time.time() * 1000)
        try:
            result = await super().call_tool(
                name,
                arguments,
            )
        except Exception as e:
            end_time = int(time.time() * 1000)
            logger.error(
                f"Error calling tool: {name} with arguments: {arguments} "
                + f"in {end_time - start_time}ms: {e}"
            )
            await self.usage_tracker.emit_tool_called_event(
                tool_called_event=ToolCalledEvent(
                    tool_name=name,
                    arguments=arguments,
                    start_time_ms=start_time,
                    end_time_ms=end_time,
                    error_message=str(e),
                ),
            )
            return [
                TextContent(
                    type="text",
                    text=str(e),
                )
            ]
        end_time = int(time.time() * 1000)
        logger.info(f"Tool {name} called successfully in {end_time - start_time}ms")
        await self.usage_tracker.emit_tool_called_event(
            tool_called_event=ToolCalledEvent(
                tool_name=name,
                arguments=arguments,
                start_time_ms=start_time,
                end_time_ms=end_time,
                error_message=None,
            ),
        )
        return result


@asynccontextmanager
async def app_lifespan(server: FastMCP[Any]) -> AsyncIterator[bool | None]:
    if not isinstance(server, DbtMCP):
        raise TypeError("app_lifespan can only be used with DbtMCP servers")
    logger.info("Starting MCP server")
    try:
        # register proxied tools inside the app lifespan to ensure the StreamableHTTP client (specific
        # to dbt Platform connection) lives on the same event loop as the running server
        # this avoids anyio cancel scope violations (see issue #498)
        if server.config.proxied_tool_config_provider:
            logger.info("Registering proxied tools")
            await register_proxied_tools(
                dbt_mcp=server,
                config_provider=server.config.proxied_tool_config_provider,
                disabled_tools=set(server.config.disable_tools),
                enabled_tools=(
                    set(server.config.enable_tools)
                    if server.config.enable_tools is not None
                    else None
                ),
                enabled_toolsets=server.config.enabled_toolsets,
                disabled_toolsets=server.config.disabled_toolsets,
            )

        yield None
    except Exception as e:
        logger.error(f"Error in MCP server: {e}")
        raise e
    finally:
        logger.info("Shutting down MCP server")
        try:
            await ProxiedToolsManager.close()
        except Exception:
            logger.exception("Error closing proxied tools manager")
        try:
            if server.lsp_client_provider:
                await server.lsp_client_provider.cleanup_connections()
        except Exception:
            logger.exception("Error cleaning up LSP connection")
        try:
            shutdown()
        except Exception:
            logger.exception("Error shutting down MCP server")


async def create_dbt_mcp(config: Config) -> DbtMCP:
    logger.info(
        "FastMCP config resolved: transport=%s host=%s port=%s api_key_set=%s",
        config.mcp_server_config.transport,
        config.mcp_server_config.host,
        config.mcp_server_config.port,
        bool(config.mcp_server_config.api_key),
    )
    auth_settings = None
    token_verifier = None
    if config.mcp_server_config.api_key:
        auth_settings = AuthSettings(
            issuer_url="http://localhost",
            resource_server_url=None,
            required_scopes=[],
        )
        token_verifier = ApiKeyTokenVerifier(config.mcp_server_config.api_key)

    dbt_mcp = DbtMCP(
        config=config,
        usage_tracker=DefaultUsageTracker(
            credentials_provider=config.credentials_provider,
            session_id=uuid.uuid4(),
        ),
        name="dbt",
        lifespan=app_lifespan,
        auth=auth_settings,
        token_verifier=token_verifier,
        host=config.mcp_server_config.host,
        port=config.mcp_server_config.port,
    )

    disabled_tools = set(config.disable_tools)
    enabled_tools = (
        set(config.enable_tools) if config.enable_tools is not None else None
    )
    enabled_toolsets = config.enabled_toolsets
    disabled_toolsets = config.disabled_toolsets
    logger.info(
        "Toolset filters: enabled_toolsets=%s disabled_toolsets=%s enabled_tools=%s disabled_tools=%s",
        sorted([toolset.value for toolset in enabled_toolsets]),
        sorted([toolset.value for toolset in disabled_toolsets]),
        sorted([tool.value for tool in enabled_tools]) if enabled_tools else [],
        sorted([tool.value for tool in disabled_tools]),
    )

    # Register MCP server tools (always available)
    logger.info("Registering MCP server tools")
    register_mcp_server_tools(
        dbt_mcp,
        disabled_tools=disabled_tools,
        enabled_tools=enabled_tools,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
    )

    if config.semantic_layer_config_provider:
        logger.info("Registering semantic layer tools")
        register_sl_tools(
            dbt_mcp,
            config_provider=config.semantic_layer_config_provider,
            client_provider=DefaultSemanticLayerClientProvider(
                config_provider=config.semantic_layer_config_provider,
            ),
            disabled_tools=disabled_tools,
            enabled_tools=enabled_tools,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )

    if config.discovery_config_provider:
        logger.info("Registering discovery tools")
        register_discovery_tools(
            dbt_mcp,
            config.discovery_config_provider,
            disabled_tools=disabled_tools,
            enabled_tools=enabled_tools,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )

    if config.dbt_cli_config:
        logger.info("Registering dbt cli tools")
        register_dbt_cli_tools(
            dbt_mcp,
            config=config.dbt_cli_config,
            disabled_tools=disabled_tools,
            enabled_tools=enabled_tools,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )

    if config.dbt_codegen_config:
        logger.info("Registering dbt codegen tools")
        register_dbt_codegen_tools(
            dbt_mcp,
            config=config.dbt_codegen_config,
            disabled_tools=disabled_tools,
            enabled_tools=enabled_tools,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )

    if config.metricflow_config:
        logger.info("Registering MetricFlow CLI tools")
        register_metricflow_tools(
            dbt_mcp,
            config=config.metricflow_config,
            disabled_tools=disabled_tools,
            enabled_tools=enabled_tools,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )

    if config.admin_api_config_provider:
        logger.info("Registering dbt admin API tools")
        register_admin_api_tools(
            dbt_mcp,
            config.admin_api_config_provider,
            disabled_tools=disabled_tools,
            enabled_tools=enabled_tools,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )

    if config.lsp_config and config.lsp_config.lsp_binary_info:
        logger.info("Registering LSP tools")
        lsp_client_provider = ProjectLSPClientProvider(
            lsp_binary_info=config.lsp_config.lsp_binary_info,
        )
        dbt_mcp.lsp_client_provider = lsp_client_provider
        await register_lsp_tools(
            dbt_mcp,
            lsp_client_provider,
            config.lsp_config.project_root_dir,
            disabled_tools=disabled_tools,
            enabled_tools=enabled_tools,
            enabled_toolsets=enabled_toolsets,
            disabled_toolsets=disabled_toolsets,
        )

    return dbt_mcp
