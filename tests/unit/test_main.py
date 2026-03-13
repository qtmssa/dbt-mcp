from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from dbt_mcp.main import main


def _mock_config(transport: str = "stdio"):
    return SimpleNamespace(
        mcp_server_config=SimpleNamespace(
            transport=transport,
            host="127.0.0.1",
            port=8000,
            api_key=None,
        )
    )


def test_main_handles_keyboard_interrupt_gracefully():
    config = _mock_config()
    server = Mock()
    server.run.side_effect = KeyboardInterrupt()
    create_server_coro = object()

    with (
        patch("dbt_mcp.main.load_config", return_value=config),
        patch(
            "dbt_mcp.main.create_dbt_mcp",
            new=Mock(return_value=create_server_coro),
        ),
        patch("dbt_mcp.main.asyncio.run", return_value=server),
        patch("dbt_mcp.main.logger") as mock_logger,
    ):
        main()

    server.run.assert_called_once_with(transport="stdio")
    mock_logger.info.assert_any_call(
        "Shutdown requested; exiting dbt-mcp gracefully."
    )


def test_main_handles_client_disconnect_gracefully():
    config = _mock_config()
    server = Mock()
    server.run.side_effect = ExceptionGroup(
        "client disconnected",
        [BrokenPipeError()],
    )
    create_server_coro = object()

    with (
        patch("dbt_mcp.main.load_config", return_value=config),
        patch(
            "dbt_mcp.main.create_dbt_mcp",
            new=Mock(return_value=create_server_coro),
        ),
        patch("dbt_mcp.main.asyncio.run", return_value=server),
        patch("dbt_mcp.main.logger") as mock_logger,
    ):
        main()

    server.run.assert_called_once_with(transport="stdio")
    mock_logger.info.assert_any_call(
        "Client disconnected; exiting dbt-mcp gracefully."
    )


def test_main_reraises_unexpected_exceptions():
    config = _mock_config()
    server = Mock()
    server.run.side_effect = RuntimeError("boom")
    create_server_coro = object()

    with (
        patch("dbt_mcp.main.load_config", return_value=config),
        patch(
            "dbt_mcp.main.create_dbt_mcp",
            new=Mock(return_value=create_server_coro),
        ),
        patch("dbt_mcp.main.asyncio.run", return_value=server),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            main()


def test_main_exits_gracefully_on_config_error():
    with (
        patch("dbt_mcp.main.load_config", side_effect=ValueError("bad env")),
        patch("dbt_mcp.main.logger") as mock_logger,
    ):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    mock_logger.error.assert_called_once_with(
        "Configuration error. dbt-mcp is exiting gracefully: %s",
        "bad env",
    )
