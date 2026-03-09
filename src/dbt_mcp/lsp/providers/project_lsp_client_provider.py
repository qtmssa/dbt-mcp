"""Project-aware LSP client provider."""

from __future__ import annotations

from dbt_mcp.lsp.lsp_binary_manager import LspBinaryInfo
from dbt_mcp.lsp.lsp_client import LSPClient
from dbt_mcp.lsp.providers.lsp_client_provider import (
    LSPClientProvider,
    LSPClientProtocol,
)
from dbt_mcp.lsp.providers.local_lsp_connection_provider import (
    LocalLSPConnectionProvider,
)


class ProjectLSPClientProvider(LSPClientProvider):
    """Manage LSP clients across multiple project directories."""

    def __init__(
        self,
        lsp_binary_info: LspBinaryInfo,
        *,
        timeout: float | None = None,
    ) -> None:
        self.lsp_binary_info = lsp_binary_info
        self.timeout = timeout
        self._connection_providers: dict[str, LocalLSPConnectionProvider] = {}

    async def get_client(
        self, project_dir: str, timeout: float | None = None
    ) -> LSPClientProtocol:
        provider = self._connection_providers.get(project_dir)
        if provider is None:
            provider = LocalLSPConnectionProvider(
                lsp_binary_info=self.lsp_binary_info,
                project_dir=project_dir,
            )
            self._connection_providers[project_dir] = provider

        connection = await provider.get_connection()
        return LSPClient(
            lsp_connection=connection,
            timeout=timeout or self.timeout,
        )

    async def cleanup_connections(self) -> None:
        for provider in self._connection_providers.values():
            await provider.cleanup_connection()
        self._connection_providers.clear()
