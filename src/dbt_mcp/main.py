import asyncio
import logging

from dbt_mcp.config.config import load_config
from dbt_mcp.mcp.server import create_dbt_mcp

logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    logger.info(
        "FastMCP runtime config: transport=%s host=%s port=%s api_key_set=%s",
        config.mcp_server_config.transport,
        config.mcp_server_config.host,
        config.mcp_server_config.port,
        bool(config.mcp_server_config.api_key),
    )
    server = asyncio.run(create_dbt_mcp(config))
    server.run(transport=config.mcp_server_config.transport)


if __name__ == "__main__":
    main()
