import asyncio
import logging

import anyio
from pydantic import ValidationError

from dbt_mcp.config.config import load_config
from dbt_mcp.errors import BinaryExecutionError
from dbt_mcp.mcp.server import create_dbt_mcp

logger = logging.getLogger(__name__)

GRACEFUL_SHUTDOWN_EXCEPTIONS = (
    KeyboardInterrupt,
    BrokenPipeError,
    EOFError,
    anyio.BrokenResourceError,
    anyio.ClosedResourceError,
)


def _iter_nested_exceptions(exc: BaseException):
    if isinstance(exc, BaseExceptionGroup):
        for child in exc.exceptions:
            yield from _iter_nested_exceptions(child)
        return
    yield exc


def _is_graceful_shutdown_exception(exc: BaseException) -> bool:
    leaf_exceptions = tuple(_iter_nested_exceptions(exc))
    return bool(leaf_exceptions) and all(
        isinstance(leaf_exc, GRACEFUL_SHUTDOWN_EXCEPTIONS)
        for leaf_exc in leaf_exceptions
    )


def _contains_exception_type(
    exc: BaseException, expected_type: type[BaseException]
) -> bool:
    return any(
        isinstance(leaf_exc, expected_type) for leaf_exc in _iter_nested_exceptions(exc)
    )


def main() -> None:
    try:
        config = load_config()
    except (ValidationError, ValueError, BinaryExecutionError) as exc:
        logger.error(
            "Configuration error. dbt-mcp is exiting gracefully: %s", str(exc)
        )
        raise SystemExit(1) from None
    logger.info(
        "FastMCP runtime config: transport=%s host=%s port=%s api_key_set=%s",
        config.mcp_server_config.transport,
        config.mcp_server_config.host,
        config.mcp_server_config.port,
        bool(config.mcp_server_config.api_key),
    )
    try:
        server = asyncio.run(create_dbt_mcp(config))
        server.run(transport=config.mcp_server_config.transport)
    except BaseException as exc:
        if not _is_graceful_shutdown_exception(exc):
            raise
        if _contains_exception_type(exc, KeyboardInterrupt):
            logger.info("Shutdown requested; exiting dbt-mcp gracefully.")
        else:
            logger.info("Client disconnected; exiting dbt-mcp gracefully.")


if __name__ == "__main__":
    main()
